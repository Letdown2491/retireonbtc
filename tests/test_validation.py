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

