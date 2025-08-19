import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from validation import validate_inputs
from config import (
    DEFAULT_CURRENT_AGE,
    DEFAULT_RETIREMENT_AGE,
    DEFAULT_LIFE_EXPECTANCY,
    DEFAULT_BITCOIN_GROWTH_RATE,
    DEFAULT_INFLATION_RATE,
    DEFAULT_CURRENT_HOLDINGS,
    DEFAULT_MONTHLY_INVESTMENT,
    SPENDING_MIN,
)


def test_monthly_spending_minimum_passes() -> None:
    errors = validate_inputs(
        DEFAULT_CURRENT_AGE,
        DEFAULT_RETIREMENT_AGE,
        DEFAULT_LIFE_EXPECTANCY,
        SPENDING_MIN,
        DEFAULT_BITCOIN_GROWTH_RATE,
        DEFAULT_INFLATION_RATE,
        DEFAULT_CURRENT_HOLDINGS,
        DEFAULT_MONTHLY_INVESTMENT,
    )

    assert not any(
        "Monthly spending" in error for error in errors
    ), "Monthly spending at SPENDING_MIN should pass validation"


def test_zero_monthly_investment_allowed_with_positive_growth() -> None:
    errors = validate_inputs(
        DEFAULT_CURRENT_AGE,
        DEFAULT_RETIREMENT_AGE,
        DEFAULT_LIFE_EXPECTANCY,
        SPENDING_MIN,
        DEFAULT_BITCOIN_GROWTH_RATE,
        DEFAULT_INFLATION_RATE,
        DEFAULT_CURRENT_HOLDINGS,
        0.0,
    )

    assert not errors, (
        "Zero monthly investment should pass validation even when growth rate is positive"
    )


def test_negative_monthly_investment_fails() -> None:
    errors = validate_inputs(
        DEFAULT_CURRENT_AGE,
        DEFAULT_RETIREMENT_AGE,
        DEFAULT_LIFE_EXPECTANCY,
        SPENDING_MIN,
        DEFAULT_BITCOIN_GROWTH_RATE,
        DEFAULT_INFLATION_RATE,
        DEFAULT_CURRENT_HOLDINGS,
        -1.0,
    )

    assert any(
        "Monthly investment" in error for error in errors
    ), "Negative monthly investment should fail validation"

