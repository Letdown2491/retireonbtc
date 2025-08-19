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


def calculate_future_value(monthly_investment, years, annual_growth_rate):
    """Calculate future value of regular monthly investments with monthly compounding"""
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
    annual_expense_at_retirement = (
        monthly_spending * 12 * (1 + inflation_rate / 100) ** years_until_retirement
    )

    # Calculate total future expenses during retirement
    total_retirement_expenses = calculate_total_future_expenses(
        annual_expense_at_retirement, retirement_duration, inflation_rate
    )

    # Calculate future Bitcoin price at retirement
    future_bitcoin_price = current_bitcoin_price * (1 + bitcoin_growth_rate / 100) ** years_until_retirement

    # Calculate Bitcoin needed at retirement
    bitcoin_needed = total_retirement_expenses / future_bitcoin_price

    # Calculate future value of monthly investments in dollars
    future_investment_value = calculate_future_value(
        monthly_investment, years_until_retirement, bitcoin_growth_rate
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

