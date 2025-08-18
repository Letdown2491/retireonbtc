# calculations.py

def calculate_future_value(monthly_investment, years, annual_growth_rate):
    """Calculate future value of regular monthly investments with monthly compounding"""
    if annual_growth_rate == 0:
        return monthly_investment * years * 12
    monthly_rate = annual_growth_rate / 100 / 12
    return monthly_investment * (((1 + monthly_rate)**(years*12) - 1) / monthly_rate) * (1 + monthly_rate)

def calculate_total_future_expenses(annual_expense, years, inflation_rate):
    """Calculate total future expenses with inflation"""
    return annual_expense * (((1 + inflation_rate/100)**years - 1) / (inflation_rate/100)) * (1 + inflation_rate/100)

def calculate_bitcoin_needed(monthly_spending, current_age, retirement_age, life_expectancy,
                           bitcoin_growth_rate, inflation_rate, current_holdings, monthly_investment, current_bitcoin_price):
    """Calculate the Bitcoin needed for retirement considering inflation and growth rates"""
    # Calculate years until retirement and retirement duration
    years_until_retirement = retirement_age - current_age
    retirement_duration = life_expectancy - retirement_age

    # Calculate inflation-adjusted annual expense at retirement
    annual_expense_at_retirement = monthly_spending * 12 * (1 + inflation_rate / 100) ** years_until_retirement

    # Calculate total future expenses during retirement
    total_retirement_expenses = calculate_total_future_expenses(
        annual_expense_at_retirement, retirement_duration, inflation_rate
    )

    # Calculate future Bitcoin price at retirement
    future_bitcoin_price = current_bitcoin_price * (1 + bitcoin_growth_rate / 100) ** years_until_retirement

    # Calculate Bitcoin needed at retirement
    bitcoin_needed = total_retirement_expenses / future_bitcoin_price

    # Calculate future value of monthly investments in dollars
    future_investment_value = calculate_future_value(monthly_investment,
                                                   years_until_retirement, bitcoin_growth_rate)

    # Calculate how many Bitcoin the investments will buy at retirement
    bitcoin_from_investments = future_investment_value / future_bitcoin_price

    # Calculate total Bitcoin holdings at retirement
    total_bitcoin_holdings = current_holdings + bitcoin_from_investments

    return bitcoin_needed, life_expectancy, total_bitcoin_holdings, future_investment_value, annual_expense_at_retirement, future_bitcoin_price, total_retirement_expenses
