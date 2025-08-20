# utils.py
import json
import logging
import secrets
import time
from datetime import datetime

import requests
import streamlit as st

from config import (
    BITCOIN_GROWTH_RATE_OPTIONS,
    DEFAULT_CURRENT_AGE,
    DEFAULT_CURRENT_HOLDINGS,
    DEFAULT_INFLATION_RATE,
    DEFAULT_LIFE_EXPECTANCY,
    DEFAULT_MONTHLY_INVESTMENT,
    DEFAULT_MONTHLY_SPENDING,
    DEFAULT_RETIREMENT_AGE,
)

_secure_random = secrets.SystemRandom()

def initialize_session_state():
    """Initialize the Streamlit session state variables.

    Examples
    --------
    >>> initialize_session_state()
    >>> st.session_state.setdefault("extra_key", "default")
    """
    st.session_state.setdefault("scenarios", [])
    st.session_state.setdefault("last_inputs", {})
    st.session_state.setdefault("clear_results", False)
    st.session_state.setdefault("calculator_expanded", True)
    st.session_state.setdefault("results_expanded", False)
    st.session_state.setdefault("results_available", False)


DEFAULT_GROWTH_RATE_LABEL = list(BITCOIN_GROWTH_RATE_OPTIONS.keys())[0]

QUERY_PARAM_DEFAULTS = {
    "current_age": DEFAULT_CURRENT_AGE,
    "retirement_age": DEFAULT_RETIREMENT_AGE,
    "life_expectancy": DEFAULT_LIFE_EXPECTANCY,
    "monthly_spending": DEFAULT_MONTHLY_SPENDING,
    "bitcoin_growth_rate_label": DEFAULT_GROWTH_RATE_LABEL,
    "inflation_rate": DEFAULT_INFLATION_RATE,
    "current_holdings": DEFAULT_CURRENT_HOLDINGS,
    "monthly_investment": DEFAULT_MONTHLY_INVESTMENT,
}


def _coerce_value(value, default):
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    return str(value)


def _get_query_params():
    try:
        return st.query_params.to_dict()
    except Exception:
        return st.experimental_get_query_params()


def _set_query_params(params):
    try:
        st.query_params.update(params)
    except Exception:
        st.experimental_set_query_params(**params)


def load_from_query_params():
    """Load calculator inputs from the URL query parameters.

    Returns
    -------
    tuple
        A pair ``(inputs, all_present)`` where ``inputs`` is a dictionary of
        input values and ``all_present`` indicates whether every expected
        parameter was provided in the query string.
    """

    params = _get_query_params()
    inputs = {}
    all_present = True
    for key, default in QUERY_PARAM_DEFAULTS.items():
        raw = params.get(key)
        if isinstance(raw, list):
            raw = raw[0]
        if raw is None:
            value = default
            all_present = False
        else:
            value = _coerce_value(raw, default)
        st.session_state[key] = value
        inputs[key] = value
    return inputs, all_present


def update_query_params():
    """Update the URL query parameters from ``st.session_state``."""

    params = {
        key: str(st.session_state.get(key, default))
        for key, default in QUERY_PARAM_DEFAULTS.items()
    }
    _set_query_params(params)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_FALLBACK_PRICE = 100_000


def get_bitcoin_price(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = 2,
    fallback_price: float = DEFAULT_FALLBACK_PRICE,
    jitter: float = 0,
):
    """Fetch the current Bitcoin price from DIA API with retry logic.

    Args:
        max_attempts (int): Maximum number of attempts to fetch the price.
        base_delay (int | float): Base delay in seconds used for exponential
            backoff between retry attempts.
        fallback_price (float): Price to return if all attempts fail.
        jitter (float): Maximum additional random delay in seconds added to the
            backoff. Set to ``0`` to disable jitter.

    Returns:
        tuple: (price, warnings) where price is the current Bitcoin price in USD
            or fallback price if all attempts fail, and warnings is a list of
            warning messages generated during the process.
    """
    dia_api_url = (
        "https://api.diadata.org/v1/assetQuotation/Bitcoin/0x0000000000000000000000000000000000000000"
    )
    timeout = 10  # seconds
    warnings = []

    with requests.Session() as session:
        for attempt in range(max_attempts):
            try:
                response = session.get(dia_api_url, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                current_price = float(data["Price"])

                if current_price <= 0:
                    raise ValueError("Received invalid price")

                return current_price, warnings

            except (
                requests.exceptions.RequestException,
                ValueError,
                KeyError,
                json.JSONDecodeError,
            ) as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = (
                    f"[{timestamp}] Attempt {attempt + 1} failed to get Bitcoin price: {str(e)}"
                )
                logging.warning(message)
                warnings.append(message)
                if attempt < max_attempts - 1:
                    # Wait before retrying with exponential backoff and optional jitter
                    delay = base_delay * (2 ** attempt)
                    if jitter:
                        delay += _secure_random.uniform(0, jitter)
                    time.sleep(delay)
                continue

    # If all attempts fail, use a fallback price
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (
        f"[{timestamp}] Failed to fetch current Bitcoin price after {max_attempts} attempts. Using fallback price of ${fallback_price:,}"
    )
    logging.warning(message)
    warnings.append(message)
    return fallback_price, warnings
