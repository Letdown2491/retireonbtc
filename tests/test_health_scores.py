import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calculations import compute_health_score_basic, health_score_from_outputs


def test_compute_health_score_basic():
    assert compute_health_score_basic(2.0, 40) == 100
    assert compute_health_score_basic(1.5, 10) == 75


def test_health_score_from_outputs():
    holdings = [5, 5, 5, 3, 1, 0]
    score, details = health_score_from_outputs(
        projected_btc_at_retirement=5,
        btc_needed_at_retirement=4,
        holdings_series_btc=holdings,
        current_age=30,
        retirement_age=32,
    )
    expected_funding_ratio = 1.25
    expected_runway_years = 3
    assert details["funding_ratio"] == pytest.approx(expected_funding_ratio)
    assert details["runway_years"] == expected_runway_years
    assert details["projected_btc"] == 5
    assert details["btc_needed"] == 4
    assert score == compute_health_score_basic(expected_funding_ratio, expected_runway_years)
