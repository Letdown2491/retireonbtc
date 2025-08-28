"""Financial calculations for the Bitcoin retirement planner."""

from dataclasses import dataclass
from typing import Sequence

import numpy as np


def _clamp(x: float, lo: float, hi: float) -> float:
    """Return ``x`` bounded to the inclusive range ``[lo, hi]``."""

    return max(lo, min(x, hi))


@dataclass
class RetirementPlan:
    """Results returned from :func:`calculate_bitcoin_needed`."""

    bitcoin_needed: float
    life_expectancy: float
    total_bitcoin_holdings: float
    future_investment_value: float
    annual_expense_at_retirement: float
    future_bitcoin_price: float
    total_retirement_expenses: float


def calculate_future_value(
    monthly_investment, years, *, annual_growth_rate=None, growth_factor=None
):
    """Calculate future value of regular monthly investments with monthly compounding.

    Exactly one of ``annual_growth_rate`` or ``growth_factor`` must be provided.
    ``years`` must be non-negative.
    """
    if years < 0:
        raise ValueError("years must be non-negative")
    if (annual_growth_rate is None) == (growth_factor is None):
        raise ValueError(
            "Provide exactly one of annual_growth_rate or growth_factor"
        )
    if growth_factor is not None:
        if years <= 0:
            annual_growth_rate = 0
        else:
            annual_growth_rate = (growth_factor ** (1 / years) - 1) * 100
    monthly_rate = (annual_growth_rate or 0) / 100 / 12
    n = years * 12
    # Stable handling near zero interest to avoid catastrophic cancellation
    if abs(monthly_rate) < 1e-12:
        return monthly_investment * n
    return monthly_investment * (((1 + monthly_rate) ** n - 1) / monthly_rate) * (1 + monthly_rate)


def calculate_total_future_expenses(annual_expense, years, inflation_rate):
    """Calculate total future expenses with inflation"""
    rate = inflation_rate / 100
    if rate == 0:
        return annual_expense * years
    return annual_expense * (((1 + rate) ** years - 1) / rate) * (1 + rate)


def calculate_bitcoin_needed(
    monthly_spending,
    current_age,
    retirement_age,
    life_expectancy,
    bitcoin_growth_rate,
    inflation_rate,
    current_holdings,
    monthly_investment,
    current_bitcoin_price,
    tax_rate: float = 0.0,
) -> RetirementPlan:
    """Calculate the Bitcoin needed for retirement considering inflation and growth rates"""

    # Calculate years until retirement and retirement duration
    years_until_retirement = retirement_age - current_age
    retirement_duration = life_expectancy - retirement_age

    # Calculate inflation-adjusted annual expense at retirement
    inflation_factor = (1 + inflation_rate / 100) ** years_until_retirement
    annual_expense_at_retirement = monthly_spending * 12 * inflation_factor

    # Calculate total future expenses during retirement
    total_retirement_expenses = calculate_total_future_expenses(
        annual_expense_at_retirement, retirement_duration, inflation_rate
    )

    # Project Bitcoin prices and yearly expenses across retirement
    growth_factor = 1 + bitcoin_growth_rate / 100
    inflation_multiplier = 1 + inflation_rate / 100
    retirement_years = np.arange(
        years_until_retirement, years_until_retirement + retirement_duration
    )
    projected_prices = current_bitcoin_price * growth_factor ** retirement_years
    gross = 1.0 / max(1e-6, 1.0 - tax_rate / 100.0)
    yearly_expenses = (monthly_spending * 12 * inflation_multiplier ** retirement_years) * gross

    # Sum yearly BTC requirements to find total Bitcoin needed
    bitcoin_needed = float(np.sum(yearly_expenses / projected_prices))

    # Bitcoin price at the moment of retirement
    future_bitcoin_price = current_bitcoin_price * growth_factor ** years_until_retirement

    # Calculate future value of monthly investments in dollars
    future_investment_value = calculate_future_value(
        monthly_investment,
        years_until_retirement,
        annual_growth_rate=bitcoin_growth_rate,
    )

    # Calculate how many Bitcoin the investments will buy at retirement
    bitcoin_from_investments = future_investment_value / future_bitcoin_price

    # Calculate total Bitcoin holdings at retirement
    total_bitcoin_holdings = current_holdings + bitcoin_from_investments

    return RetirementPlan(
        bitcoin_needed=bitcoin_needed,
        life_expectancy=life_expectancy,
        total_bitcoin_holdings=total_bitcoin_holdings,
        future_investment_value=future_investment_value,
        annual_expense_at_retirement=annual_expense_at_retirement,
        future_bitcoin_price=future_bitcoin_price,
        total_retirement_expenses=total_retirement_expenses,
    )


def project_holdings_over_time(
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    bitcoin_growth_rate: float,
    inflation_rate: float,
    current_holdings: float,
    monthly_investment: float,
    monthly_spending: float,
    current_bitcoin_price: float,
    tax_rate: float = 0.0,
) -> list[float]:
    """Project Bitcoin holdings for each year.

    This helper mirrors the accumulation and spending logic from
    :func:`calculate_bitcoin_needed` by converting yearly investments to BTC
    before retirement and deducting inflated expenses during retirement.

    Args:
        current_age: User's current age.
        retirement_age: Target retirement age.
        life_expectancy: Expected lifespan.
        bitcoin_growth_rate: Annual Bitcoin growth rate in percent.
        inflation_rate: Annual inflation rate in percent.
        current_holdings: Current Bitcoin holdings in BTC.
        monthly_investment: Monthly investment amount in USD.
        monthly_spending: Monthly spending requirement in USD (today's value).
        current_bitcoin_price: Current Bitcoin price in USD.

    Returns:
        A list of BTC holdings for each year from ``current_age`` up to and
        including ``life_expectancy``.

    Raises:
        ValueError: If ``retirement_age`` exceeds ``life_expectancy``.
    """

    if retirement_age > life_expectancy:
        raise ValueError("retirement_age must be less than or equal to life_expectancy")

    years = life_expectancy - current_age + 1
    years_until_retirement = retirement_age - current_age

    growth_multiplier = 1 + bitcoin_growth_rate / 100
    inflation_multiplier = 1 + inflation_rate / 100

    price_factors = np.cumprod(np.r_[1, np.full(years - 1, growth_multiplier)])
    prices = current_bitcoin_price * price_factors

    annual_expense_at_retirement = (
        monthly_spending * 12 * inflation_multiplier ** years_until_retirement
    )

    pre_retirement_years = max(years_until_retirement, 0)
    post_retirement_years = years - pre_retirement_years

    expense_factors = np.cumprod(
        np.r_[1, np.full(max(post_retirement_years - 1, 0), inflation_multiplier)]
    )
    gross = 1.0 / max(1e-6, 1.0 - tax_rate / 100.0)
    expenses_after_retirement = (annual_expense_at_retirement * expense_factors) * gross
    expenses_usd = np.concatenate(
        [np.zeros(pre_retirement_years), expenses_after_retirement]
    )

    investments_usd = np.concatenate(
        [
            np.full(pre_retirement_years, monthly_investment * 12),
            np.zeros(post_retirement_years),
        ]
    )

    btc_change = (investments_usd - expenses_usd) / prices

    holdings = current_holdings + np.cumsum(btc_change)
    holdings = np.maximum(holdings, 0)

    return holdings.tolist()


def compute_health_score_basic(funding_ratio: float, runway_years: float) -> int:
    """Compute a simple health score based on funding and runway.

    The funding ratio represents available BTC divided by BTC required. Values
    are capped at ``1.5`` (150%). Runway years indicate how long funds last
    after retirement and are normalized against a 20-year horizon. The final
    score is an integer in the range ``0`` to ``100``.
    """

    funding_component = _clamp(funding_ratio, 0.0, 1.5) / 1.5
    runway_component = _clamp(runway_years / 20.0, 0.0, 1.0)
    score = (funding_component + runway_component) / 2 * 100
    return int(round(_clamp(score, 0.0, 100.0)))


def health_score_from_outputs(
    projected_btc_at_retirement: float,
    btc_needed_at_retirement: float,
    holdings_series_btc: Sequence[float],
    current_age: int,
    retirement_age: int,
    life_expectancy: int | None = None,
) -> tuple[int, dict[str, float]]:
    """Derive a basic health score from model outputs.

    Args:
        projected_btc_at_retirement: BTC expected to be held at retirement.
        btc_needed_at_retirement: BTC required at retirement age.
        holdings_series_btc: Yearly BTC holdings from ``current_age`` onward.
        current_age: Present age.
        retirement_age: Target retirement age.
        life_expectancy: Optional life expectancy overriding inference from
            ``holdings_series_btc``.

    Returns:
        A tuple ``(score, details)`` where ``score`` is the health score and
        ``details`` contains intermediate metrics.
    """

    holdings = list(holdings_series_btc)
    if life_expectancy is None:
        life_expectancy = current_age + len(holdings) - 1

    start_index = max(0, retirement_age - current_age)
    runway_years = 0
    for h in holdings[start_index:]:
        if h > 0:
            runway_years += 1
        else:
            break

    if btc_needed_at_retirement == 0:
        funding_ratio = float("inf")
    else:
        funding_ratio = projected_btc_at_retirement / btc_needed_at_retirement

    score = compute_health_score_basic(funding_ratio, runway_years)
    details = {
        "funding_ratio": funding_ratio,
        "runway_years": runway_years,
        "projected_btc": projected_btc_at_retirement,
        "btc_needed": btc_needed_at_retirement,
    }
    return score, details
