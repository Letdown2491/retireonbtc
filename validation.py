# validation.py
from config import AGE_RANGE, SPENDING_MIN, RATE_MIN, HOLDINGS_MAX

def validate_inputs(current_age, retirement_age, life_expectancy, monthly_spending,
                   bitcoin_growth_rate, inflation_rate, current_holdings, monthly_investment):
    """Validate all user inputs and return any errors found"""
    errors = []

    if not AGE_RANGE[0] <= current_age <= AGE_RANGE[1]:
        errors.append(f"Current age must be between {AGE_RANGE[0]} and {AGE_RANGE[1]}")

    if retirement_age <= current_age or not AGE_RANGE[0] <= retirement_age <= AGE_RANGE[1]:
        errors.append(f"Retirement age must be greater than current age and between {AGE_RANGE[0]} and {AGE_RANGE[1]}")

    if life_expectancy <= retirement_age or not AGE_RANGE[0] <= life_expectancy <= AGE_RANGE[1]:
        errors.append(f"Life expectancy must be greater than retirement age and between {AGE_RANGE[0]} and {AGE_RANGE[1]}")

    if monthly_spending < SPENDING_MIN:
        errors.append(f"Monthly spending must be at least {SPENDING_MIN}")

    if bitcoin_growth_rate < RATE_MIN:
        errors.append("Bitcoin growth rate cannot be negative")

    if inflation_rate < RATE_MIN:
        errors.append("Inflation rate cannot be negative")

    if current_holdings < RATE_MIN or current_holdings > HOLDINGS_MAX:
        errors.append("Current Bitcoin holdings must be between 0 and 21,000,000")

    if monthly_investment < RATE_MIN:
        errors.append("Monthly investment cannot be negative")

    if bitcoin_growth_rate > RATE_MIN and monthly_investment == RATE_MIN:
        errors.append("Monthly investment must be positive if growth rate is positive")

    return errors
