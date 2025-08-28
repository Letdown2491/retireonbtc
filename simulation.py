import numpy as np

def simulate_regime_shift_returns(years: int, n_sims: int, seed: int | None = None) -> np.ndarray:
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
    # Convert to growth factors
    return (1.0 + returns).astype(np.float32)


def simulate_holdings_paths(
    return_factors: np.ndarray,
    current_age: int,
    retirement_age: int,
    current_holdings: float,
    monthly_investment: float,
    monthly_spending: float,
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
    spend_btc = (
        (np.float32(monthly_spending) * 12.0) / prices[:, years_until_retirement:]
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
    percentiles: tuple[int, ...] = (10, 25, 50, 75),
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

    for t in range(years):
        # Update holdings pre/post retirement using current price
        if t < years_until_retirement:
            h = h + (np.float32(monthly_investment) * 12.0) / price
        else:
            h = np.maximum(h - (np.float32(monthly_spending) * 12.0) / price, 0.0)
            alive &= (h > 0)

        # Update price (end-of-period growth) for next step
        price = price * rf[:, t]

        # Compute USD value and append percentiles for this year
        values_t = h * price
        for p in percentiles:
            pct_series[f"p{p}"].append(float(np.percentile(values_t, p)))

    prob_not_run_out = float(np.mean(alive)) if years_until_retirement < years else 1.0
    return pct_series, prob_not_run_out
