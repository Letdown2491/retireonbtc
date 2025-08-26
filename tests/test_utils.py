import os
import sys
import requests
import time
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import get_bitcoin_price


def test_get_bitcoin_price_exponential_backoff(monkeypatch):
    session_instances = []

    class MockSession:
        def __init__(self):
            session_instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "Session", MockSession)

    sleep_calls = []

    def mock_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(time, "sleep", mock_sleep)

    price, warnings = get_bitcoin_price(max_attempts=3, base_delay=2)

    assert price == 100000
    assert len(warnings) == 4
    assert sleep_calls == [2, 4]
    assert len(session_instances) == 1


def test_get_bitcoin_price_malformed_json(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise json.JSONDecodeError("Expecting value", "", 0)

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(requests, "Session", MockSession)

    price, warnings = get_bitcoin_price(max_attempts=1)

    assert price == 100000
    assert len(warnings) == 2


def test_get_bitcoin_price_missing_usd(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {}

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(requests, "Session", MockSession)

    price, warnings = get_bitcoin_price(max_attempts=1)

    assert price == 100000
    assert len(warnings) == 2


def test_get_bitcoin_price_non_positive_usd(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"USD": 0}

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(requests, "Session", MockSession)

    price, warnings = get_bitcoin_price(max_attempts=1)

    assert price == 100000
    assert len(warnings) == 2


def test_get_bitcoin_price_success(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"USD": 12345.67}

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(requests, "Session", MockSession)

    price, warnings = get_bitcoin_price(max_attempts=1)

    assert price == 12345.67
    assert warnings == []


def test_get_bitcoin_price_quick_fail(monkeypatch):
    request_calls = []

    class MockSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, *args, **kwargs):
            request_calls.append(1)
            raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "Session", MockSession)

    sleep_calls = []

    def mock_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(time, "sleep", mock_sleep)

    price, warnings = get_bitcoin_price(max_attempts=5, base_delay=1, quick_fail=True)

    assert price == 100000
    assert len(warnings) == 2
    assert len(request_calls) == 1
    assert sleep_calls == []
