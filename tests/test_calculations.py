import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calculations import (
    calculate_bitcoin_needed,
    calculate_future_value,
    calculate_total_future_expenses,
    project_holdings_over_time,
)


def test_calculate_bitcoin_needed_equivalence():
    monthly_spending = 3000
    current_age = 30
    retirement_age = 65
    life_expectancy = 85
    bitcoin_growth_rate = 5
    inflation_rate = 2
    current_holdings = 1.5
    monthly_investment = 500
    current_bitcoin_price = 30000

    plan = calculate_bitcoin_needed(
        monthly_spending,
        current_age,
        retirement_age,
        life_expectancy,
        bitcoin_growth_rate,
        inflation_rate,
        current_holdings,
        monthly_investment,
        current_bitcoin_price,
    )

    years_until_retirement = retirement_age - current_age
    retirement_duration = life_expectancy - retirement_age

    annual_expense_at_retirement = (
        monthly_spending * 12 * (1 + inflation_rate / 100) ** years_until_retirement
    )
    total_retirement_expenses = calculate_total_future_expenses(
        annual_expense_at_retirement, retirement_duration, inflation_rate
    )
    future_bitcoin_price = current_bitcoin_price * (
        (1 + bitcoin_growth_rate / 100) ** years_until_retirement
    )
    future_investment_value = calculate_future_value(
        monthly_investment,
        years_until_retirement,
        annual_growth_rate=bitcoin_growth_rate,
    )
    bitcoin_from_investments = future_investment_value / future_bitcoin_price
    total_bitcoin_holdings = current_holdings + bitcoin_from_investments
    bitcoin_needed = total_retirement_expenses / future_bitcoin_price

    assert plan.annual_expense_at_retirement == pytest.approx(
        annual_expense_at_retirement
    )
    assert plan.future_bitcoin_price == pytest.approx(future_bitcoin_price)
    assert plan.future_investment_value == pytest.approx(future_investment_value)
    assert plan.total_retirement_expenses == pytest.approx(total_retirement_expenses)
    assert plan.total_bitcoin_holdings == pytest.approx(total_bitcoin_holdings)
    assert plan.bitcoin_needed == pytest.approx(bitcoin_needed)


def test_project_holdings_over_time_matches_manual_calculation():
    params = dict(
        current_age=30,
        retirement_age=65,
        life_expectancy=85,
        bitcoin_growth_rate=5,
        inflation_rate=2,
        current_holdings=1.5,
        monthly_investment=500,
        monthly_spending=3000,
        current_bitcoin_price=30000,
    )

    holdings = project_holdings_over_time(**params)

    ages = range(params["current_age"], params["life_expectancy"] + 1)
    years_until_retirement = params["retirement_age"] - params["current_age"]
    annual_expense_at_retirement = (
        params["monthly_spending"]
        * 12
        * (1 + params["inflation_rate"] / 100) ** years_until_retirement
    )

    expected_holdings = []
    btc_holdings = params["current_holdings"]

    for year_index, age in enumerate(ages):
        price = params["current_bitcoin_price"] * (
            1 + params["bitcoin_growth_rate"] / 100
        ) ** year_index

        if age < params["retirement_age"]:
            btc_holdings += (params["monthly_investment"] * 12) / price
        else:
            expense_year = age - params["retirement_age"]
            annual_expense = annual_expense_at_retirement * (
                1 + params["inflation_rate"] / 100
            ) ** expense_year
            btc_holdings -= annual_expense / price
            btc_holdings = max(btc_holdings, 0)

        expected_holdings.append(btc_holdings)

    assert holdings == pytest.approx(expected_holdings)


def test_project_holdings_over_time_rejects_invalid_retirement_age():
    with pytest.raises(ValueError):
        project_holdings_over_time(
            current_age=30,
            retirement_age=90,
            life_expectancy=85,
            bitcoin_growth_rate=5,
            inflation_rate=2,
            current_holdings=1.5,
            monthly_investment=500,
            monthly_spending=3000,
            current_bitcoin_price=30000,
        )


def test_calculate_future_value_requires_single_parameter():
    with pytest.raises(ValueError):
        calculate_future_value(100, 10)
    with pytest.raises(ValueError):
        calculate_future_value(
            100, 10, annual_growth_rate=5, growth_factor=1.5
        )
