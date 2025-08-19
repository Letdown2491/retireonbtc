# utils.py
import logging
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

def get_bitcoin_price(max_attempts=3):
    """
    Fetch the current Bitcoin price from DIA API with retry logic.

    Args:
        max_attempts (int): Maximum number of attempts to fetch the price

    Returns:
        tuple: (price, warnings) where price is the current Bitcoin price in USD
               or fallback price if all attempts fail, and warnings is a list
               of warning messages generated during the process
    """
    dia_api_url = "https://api.diadata.org/v1/assetQuotation/Bitcoin/0x0000000000000000000000000000000000000000"
    timeout = 10  # seconds
    warnings = []

    for attempt in range(max_attempts):
        try:
            response = requests.get(dia_api_url, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            current_price = data.get('Price')

            if current_price is None or float(current_price) <= 0:
                raise ValueError("Received invalid price")

            return float(current_price), warnings

        except requests.exceptions.RequestException as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"[{timestamp}] Attempt {attempt + 1} failed to get Bitcoin price: {str(e)}"
            logging.warning(message)
            warnings.append(message)
            if attempt < max_attempts - 1:
                time.sleep(2)  # Wait before retrying
            continue

    # If all attempts fail, use a fallback price
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] Failed to fetch current Bitcoin price after {max_attempts} attempts. Using fallback price of $100,000"
    logging.warning(message)
    warnings.append(message)
    return 100000, warnings  # Default fallback price
