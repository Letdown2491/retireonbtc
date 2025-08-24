# Bitcoin Retirement Calculator

A Streamlit application to help you plan your retirement using Bitcoin as an investment vehicle.

[![Security](https://github.com/Letdown2491/retireonbtc/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Letdown2491/retireonbtc/actions/workflows/security.yml)

## Features
- Calculate how much Bitcoin you need to retire
- Project future BTC prices and analyze growth-rate scenarios.
- Track your progress towards retirement with a retirement health score.
- Show inflation-adjusted expenses over time.
- Vectorized projected holdings with a quick glance chart of holdings over time.
- Extensive configuration and validation options to prevent calculation errors caused by invalid user inputs.
- BTC price cached in session for snappier re-runs as well as a quick-fail option when fetching BTC price to avoid long waits on errors.

## Getting Started

Simple head over to [Retire On BTC](https://retireonbtc.xyz) to play with it yourself, or if you prefer running the project locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/Letdown2491/retireonbtc.git
   cd retireonbtc
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run main.py
   ```
