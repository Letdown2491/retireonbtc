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
    bull = rng.normal(0.3, 0.2, size=(n_sims, years))
    bear = rng.normal(-0.1, 0.25, size=(n_sims, years))
    returns = np.where(regimes, bull, bear)
    # Convert to growth factors
    return 1 + returns


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
    n_sims, years = return_factors.shape
    prices = current_bitcoin_price * np.cumprod(return_factors, axis=1)

    years_until_retirement = retirement_age - current_age
    holdings = np.zeros((n_sims, years))
    h = np.full(n_sims, current_holdings, dtype=float)

    invest_btc = (
        (monthly_investment * 12) / prices[:, :years_until_retirement]
        if years_until_retirement > 0
        else np.empty((n_sims, 0))
    )
    spend_btc = (
        (monthly_spending * 12) / prices[:, years_until_retirement:]
        if years_until_retirement < years
        else np.empty((n_sims, 0))
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
