import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import utils
from config import BITCOIN_GROWTH_RATE_OPTIONS


class QueryParamsStub(dict):
    def to_dict(self):
        return dict(self)

    def update(self, params):
        self.clear()
        super().update(params)


class StreamlitStub:
    def __init__(self):
        self.session_state = {}
        self.query_params = QueryParamsStub()


def test_query_params_round_trip(monkeypatch):
    st_stub = StreamlitStub()
    monkeypatch.setattr(utils, "st", st_stub)

    label = list(BITCOIN_GROWTH_RATE_OPTIONS.keys())[1]
    inputs = {
        "current_age": 30,
        "retirement_age": 60,
        "life_expectancy": 90,
        "monthly_spending": 4000.0,
        "bitcoin_growth_rate_label": label,
        "inflation_rate": 2.5,
        "current_holdings": 0.5,
        "monthly_investment": 250.0,
    }

    st_stub.session_state.update(inputs)
    utils.update_query_params()

    assert st_stub.query_params == {k: str(v) for k, v in inputs.items()}

    st_stub.session_state = {}
    loaded, all_present = utils.load_from_query_params()

    assert all_present
    assert loaded == inputs
    for key, value in inputs.items():
        assert isinstance(st_stub.session_state[key], type(value))


def test_load_defaults_when_missing(monkeypatch):
    st_stub = StreamlitStub()
    monkeypatch.setattr(utils, "st", st_stub)

    loaded, all_present = utils.load_from_query_params()

    assert not all_present
    assert loaded == utils.QUERY_PARAM_DEFAULTS
    for key, value in utils.QUERY_PARAM_DEFAULTS.items():
        assert st_stub.session_state[key] == value
