import numpy as np
from datetime import date
from typing import Optional
from config import (
    HALVING_ANCHOR_YEAR,
    HALVING_ANCHOR_MONTH,
    HALVING_ANCHOR_DAY,
    HALVING_CYCLE_MONTHS,
    HALVING_PHASE_PARAMS,
    HALVING_MIN_RETURN,
    PRICE_DECAY_YEARS_SCALE,
)

def simulate_regime_shift_returns(
    years: int,
    n_sims: int,
    seed: int | None = None,
    target_arith_return_pct: float | None = None,
) -> np.ndarray:
    """Simulate annual return factors using a simple two-regime model.

    Parameters
    ----------
    years:
        Number of years to simulate.
    n_sims:
        Number of simulation paths.
    seed:
        Optional random seed for reproducibility.

    Returns
    -------
    numpy.ndarray
        Array of shape ``(n_sims, years)`` containing multiplicative return
        factors (``1 + r``) for each year and simulation.
    """
    rng = np.random.default_rng(seed)
    # Bernoulli draw for bull (True) or bear (False) regime
    regimes = rng.random((n_sims, years)) < 0.5
    bull = rng.normal(0.3, 0.2, size=(n_sims, years)).astype(np.float32)
    bear = rng.normal(-0.1, 0.25, size=(n_sims, years)).astype(np.float32)
    returns = np.where(regimes, bull, bear).astype(np.float32)
    # Align arithmetic mean annual return to the selected growth rate, if provided
    if target_arith_return_pct is not None:
        base_mean = np.float32(0.5 * 0.3 + 0.5 * (-0.1))  # 10% baseline
        target_mean = np.float32(target_arith_return_pct) / np.float32(100.0)
        shift = target_mean - base_mean
        returns = returns + np.float32(shift)
    # Convert to growth factors
    return (1.0 + returns).astype(np.float32)

def _compute_halving_phases(years: int, now: Optional[date] = None) -> np.ndarray:
    """Return array of phase indices (0..3) for each simulated year."""
    if now is None:
        now = date.today()
    anchor = date(HALVING_ANCHOR_YEAR, HALVING_ANCHOR_MONTH, HALVING_ANCHOR_DAY)
    months_since_anchor = (now.year - anchor.year) * 12 + (now.month - anchor.month)
    midyear_offsets = (months_since_anchor + (np.arange(years) * 12) + 6) % HALVING_CYCLE_MONTHS
    return (midyear_offsets // 12).astype(int)


def compute_mu_log_schedule(
    years: int,
    target_arith_return_pct: Optional[float] = None,
    now: Optional[date] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-year log-drift (mu_log) and log-vol (sigma_log) schedules.

    - Uses a diminishing-returns schedule: mu_log[y] = mu0 / (1 + y / PRICE_DECAY_YEARS_SCALE)
      where mu0 = ln(1 + growth_rate).
    - Adds a zero-centered halving-phase tilt based on HALVING_PHASE_PARAMS' first element.
    - Returns (mu_log_year, sigma_log_year) arrays of length ``years``.
    """
    phases = _compute_halving_phases(years, now=now)

    # Phase tilt and vol
    phase_mu_arith = np.array([p[0] for p in HALVING_PHASE_PARAMS], dtype=np.float32)
    phase_sigma_log = np.array([p[1] for p in HALVING_PHASE_PARAMS], dtype=np.float32)
    # Convert arithmetic tilts to log-space and zero-center
    phase_mu_log_raw = np.log1p(phase_mu_arith.astype(np.float64)).astype(np.float32)
    phase_mu_log_tilt = phase_mu_log_raw - np.mean(phase_mu_log_raw).astype(np.float32)

    # Diminishing-returns baseline from user growth rate (CAGR)
    if target_arith_return_pct is not None:
        g = np.float32(target_arith_return_pct) / np.float32(100.0)
    else:
        g = np.float32(0.10)
    mu0 = np.log1p(g).astype(np.float32)
    y = np.arange(years, dtype=np.float32)
    decay = 1.0 / (1.0 + (y / np.float32(PRICE_DECAY_YEARS_SCALE)))
    mu_log_year = mu0 * decay + phase_mu_log_tilt[phases]
    sigma_log_year = phase_sigma_log[phases]
    return mu_log_year.astype(np.float32), sigma_log_year.astype(np.float32)


def generate_halving_returns(
    years: int,
    n_sims: int,
    seed: Optional[int] = None,
    target_arith_return_pct: Optional[float] = None,
    now: Optional[date] = None,
) -> np.ndarray:
    """Generate annual growth factors anchored to the Bitcoin halving cycle.

    Uses a 48-month cycle starting from the April 2024 halving. Each year in the
    simulation is assigned to one of four 12-month phases with distinct mean and
    volatility. A constant drift shift is applied to align the realized average
    arithmetic return to ``target_arith_return_pct`` while preserving cycle shape.
    """
    rng = np.random.default_rng(seed)
    mu_log_year, sigma_log_year = compute_mu_log_schedule(
        years, target_arith_return_pct=target_arith_return_pct, now=now
    )
    # Sample log-returns z ~ N(mu_log_year, sigma_log_year)
    mu_mat = np.broadcast_to(mu_log_year, (n_sims, years)).astype(np.float32)
    sigma_mat = np.broadcast_to(sigma_log_year, (n_sims, years)).astype(np.float32)
    z = rng.normal(loc=mu_mat, scale=sigma_mat).astype(np.float32)

    # Growth factors are exp(z); no negative factors and geometric alignment holds
    factors = np.exp(z, dtype=np.float32)
    return factors


def simulate_holdings_paths(
    return_factors: np.ndarray,
    current_age: int,
    retirement_age: int,
    current_holdings: float,
    monthly_investment: float,
    monthly_spending: float,
    tax_rate: float,
    current_bitcoin_price: float,
) -> tuple[np.ndarray, float]:
    """Simulate portfolio value paths (USD) given return factors.

    Parameters
    ----------
    return_factors:
        Array of shape ``(n_sims, years)`` of annual growth factors.
    current_age, retirement_age:
        Ages defining the simulation horizon and when spending begins.
    current_holdings:
        Current BTC holdings.
    monthly_investment:
        USD invested every month before retirement.
    monthly_spending:
        USD spent every month after retirement.
    current_bitcoin_price:
        Present BTC price used as the starting point.

    Returns
    -------
    tuple
        ``(paths, prob_not_run_out)`` where ``paths`` is an array of USD
        portfolio values for each simulation and year and
        ``prob_not_run_out`` is the probability that funds remain positive
        through retirement.
    """
    # Ensure a compact dtype for performance/memory
    rf = np.asarray(return_factors, dtype=np.float32)
    n_sims, years = rf.shape
    prices = np.float32(current_bitcoin_price) * np.cumprod(rf, axis=1, dtype=np.float32)

    years_until_retirement = retirement_age - current_age
    holdings = np.zeros((n_sims, years), dtype=np.float32)
    h = np.full(n_sims, np.float32(current_holdings), dtype=np.float32)

    invest_btc = (
        (np.float32(monthly_investment) * 12.0) / prices[:, :years_until_retirement]
        if years_until_retirement > 0
        else np.empty((n_sims, 0), dtype=np.float32)
    )
    gross = np.float32(1.0) / np.float32(max(1e-6, 1.0 - (tax_rate / 100.0)))
    spend_btc = (
        (np.float32(monthly_spending) * 12.0) * gross / prices[:, years_until_retirement:]
        if years_until_retirement < years
        else np.empty((n_sims, 0), dtype=np.float32)
    )

    for t in range(years):
        if t < years_until_retirement:
            h = h + invest_btc[:, t]
        else:
            idx = t - years_until_retirement
            if idx < spend_btc.shape[1]:
                h = np.maximum(h - spend_btc[:, idx], 0.0)
        holdings[:, t] = h

    after_retirement = holdings[:, years_until_retirement:]
    if after_retirement.size:
        not_run_out = np.all(after_retirement > 0, axis=1)
        prob_not_run_out = float(np.mean(not_run_out))
    else:
        prob_not_run_out = 1.0

    values = holdings * prices
    return values, prob_not_run_out


def simulate_percentiles_and_prob(
    return_factors: np.ndarray,
    current_age: int,
    retirement_age: int,
    current_holdings: float,
    monthly_investment: float,
    monthly_spending: float,
    current_bitcoin_price: float,
    tax_rate: float = 0.0,
    percentiles: tuple[int, ...] = (10, 25, 50),
) -> tuple[dict[str, list[float]], float]:
    """Stream Monte Carlo to compute percentiles and success probability.

    Computes p10/p25/p50/p75 (by default) of USD portfolio value for each year
    without materializing the full path matrix. Also computes the probability
    of not running out of BTC during retirement.
    """
    rf = np.asarray(return_factors, dtype=np.float32)
    n_sims, years = rf.shape

    # Streaming price vector (per-sim) and holdings
    price = np.full(n_sims, np.float32(current_bitcoin_price), dtype=np.float32)
    h = np.full(n_sims, np.float32(current_holdings), dtype=np.float32)
    years_until_retirement = retirement_age - current_age
    alive = np.ones(n_sims, dtype=bool)

    # Accumulate percentile series
    pct_series = {f"p{p}": [] for p in percentiles}

    gross = np.float32(1.0) / np.float32(max(1e-6, 1.0 - (tax_rate / 100.0)))
    for t in range(years):
        # Update holdings pre/post retirement using current price
        if t < years_until_retirement:
            h = h + (np.float32(monthly_investment) * 12.0) / price
        else:
            h = np.maximum(h - (np.float32(monthly_spending) * 12.0) * gross / price, 0.0)
            alive &= (h > 0)

        # Update price (end-of-period growth) for next step
        price = price * rf[:, t]

        # Compute USD value and append percentiles for this year
        values_t = h * price
        for p in percentiles:
            pct_series[f"p{p}"].append(float(np.percentile(values_t, p)))

    prob_not_run_out = float(np.mean(alive)) if years_until_retirement < years else 1.0
    return pct_series, prob_not_run_out
