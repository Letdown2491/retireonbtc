"""Financial calculations for the Bitcoin retirement planner."""

from dataclasses import dataclass


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
    """
    if (annual_growth_rate is None) == (growth_factor is None):
        raise ValueError(
            "Provide exactly one of annual_growth_rate or growth_factor"
        )
    if growth_factor is not None:
        if years <= 0:
            annual_growth_rate = 0
        else:
            annual_growth_rate = (growth_factor ** (1 / years) - 1) * 100
    if annual_growth_rate == 0:
        return monthly_investment * years * 12
    monthly_rate = annual_growth_rate / 100 / 12
    return monthly_investment * (((1 + monthly_rate) ** (years * 12) - 1) / monthly_rate) * (1 + monthly_rate)


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

    # Calculate future Bitcoin price at retirement
    growth_factor = (1 + bitcoin_growth_rate / 100) ** years_until_retirement
    future_bitcoin_price = current_bitcoin_price * growth_factor

    # Calculate Bitcoin needed at retirement
    bitcoin_needed = total_retirement_expenses / future_bitcoin_price

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
    """

    ages = range(current_age, life_expectancy + 1)
    years_until_retirement = retirement_age - current_age
    annual_expense_at_retirement = (
        monthly_spending * 12 * (1 + inflation_rate / 100) ** years_until_retirement
    )

    holdings = []
    btc_holdings = current_holdings

    for year_index, age in enumerate(ages):
        price = current_bitcoin_price * (1 + bitcoin_growth_rate / 100) ** year_index

        if age < retirement_age:
            btc_holdings += (monthly_investment * 12) / price
        else:
            expense_year = age - retirement_age
            annual_expense = annual_expense_at_retirement * (
                1 + inflation_rate / 100
            ) ** expense_year
            btc_holdings -= annual_expense / price
            btc_holdings = max(btc_holdings, 0)

        holdings.append(btc_holdings)

    return holdings

