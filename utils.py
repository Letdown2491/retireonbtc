# utils.py
import json
import logging
import random
import requests
import streamlit as st
import time
from datetime import datetime

def initialize_session_state():
    """Initialize the Streamlit session state variables"""
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = []
    if 'last_inputs' not in st.session_state:
        st.session_state.last_inputs = {}
    if 'clear_results' not in st.session_state:
        st.session_state.clear_results = False

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
                        delay += random.uniform(0, jitter)
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
