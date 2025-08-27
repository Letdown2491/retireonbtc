# Bitcoin Retirement Calculator
A simple application to help you plan your retirement using Bitcoin as an investment vehicle. Hosted version available at [Retire On BTC](https://retireonbtc.xyz).

![GitHub License](https://img.shields.io/github/license/Letdown2491/retireonbtc?style=flat) ![GitHub repo size](https://img.shields.io/github/repo-size/Letdown2491/retireonbtc)
 [![Security](https://github.com/Letdown2491/retireonbtc/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/Letdown2491/retireonbtc/actions/workflows/security.yml) [![Dependabot Updates](https://github.com/Letdown2491/retireonbtc/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/Letdown2491/retireonbtc/actions/workflows/dependabot/dependabot-updates)


## Features
- Calculate how much Bitcoin you need to retire
- Project future BTC prices and analyze growth-rate scenarios.
- Track your progress towards retirement with a retirement health score.
- Show inflation-adjusted expenses over time.
- Vectorized projected holdings with a quick glance chart of holdings over time.
- Monte Carlo simulations to determine retirement plan success probability.
- Extensive configuration and validation options to prevent calculation errors caused by invalid user inputs.
- BTC price cached in session for snappier re-runs as well as a quick-fail option when fetching BTC price to avoid long waits on errors.
- No tracking or telemetry of any kind.

## Getting Started
[Retire On BTC](https://retireonbtc.xyz) can be run locally via Python or by using containerization tools like Docker or Podman. 

### Running via Python
   ```bash
   git clone https://github.com/Letdown2491/retireonbtc.git
   cd retireonbtc
   pip install -r requirements.txt
   streamlit run main.py
   ```

### Running via Docker or Podman
   ```bash
   git clone https://github.com/Letdown2491/retireonbtc.git
   cd retireonbtc
   docker build -t retireonbtc .
   docker run -p 8501:8501 retireonbtc
   ```

### Running via Docker Compose
   ```bash
   git clone https://github.com/Letdown2491/retireonbtc.git
   cd retireonbtc
   docker compose up --build
   ```
