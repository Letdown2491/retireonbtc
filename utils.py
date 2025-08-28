# utils.py
import json
import logging
import secrets
import requests
import streamlit as st
import time
from datetime import datetime

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

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_FALLBACK_PRICE = 100_000


def get_bitcoin_price(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = 2,
    fallback_price: float = DEFAULT_FALLBACK_PRICE,
    jitter: float = 0,
    quick_fail: bool = False,
):
    """Fetch the current Bitcoin price from the mempool.space API with retry logic.

    Args:
        max_attempts (int): Maximum number of attempts to fetch the price.
        base_delay (int | float): Base delay in seconds used for exponential
            backoff between retry attempts.
        fallback_price (float): Price to return if all attempts fail.
        jitter (float): Maximum additional random delay in seconds added to the
            backoff. Set to ``0`` to disable jitter.
        quick_fail (bool): If ``True``, call the API only once and return the
            fallback price immediately on any exception without sleeping.

    Returns:
        tuple: (price, warnings) where price is the current Bitcoin price in USD
            or fallback price if all attempts fail, and warnings is a list of
            warning messages generated during the process.
    """
    mempool_api_url = "https://mempool.space/api/v1/prices"
    timeout = 5  # seconds
    warnings = []

    with requests.Session() as session:
        attempts = 1 if quick_fail else max_attempts
        for attempt in range(attempts):
            try:
                response = session.get(mempool_api_url, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                current_price = float(data["USD"])
                if current_price <= 0:
                    raise KeyError("USD price not found or invalid")

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
                if quick_fail:
                    fallback_message = (
                        f"[{timestamp}] Failed to fetch current Bitcoin price. "
                        f"Using fallback price of ${fallback_price:,}"
                    )
                    logging.warning(fallback_message)
                    warnings.append(fallback_message)
                    return fallback_price, warnings
                if attempt < attempts - 1:
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
