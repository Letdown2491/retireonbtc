# Changelog
All notable changes to this project are documented here.  
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Dates use `YYYY-MM-DD`.

## 2025-08-19
### Added
- Progress / accumulation visualization in Plotly and related UI hooks. (PRs #15, #20)  
- Helper for projecting BTC holdings over time and integration in visualization. (PR #20)

### Changed
- Refactor: `main.py` split into helper functions for clearer orchestration. (PR #19)  
- Refactor: initialization of Streamlit session state to a cleaner `setdefault` pattern with docs. (PR #27)  
- Calculations: require exactly one of `annual_growth_rate` or `growth_factor` in future-value API. (PR #23)  
- Calculations: optimized holdings projection loop (precomputed multipliers, iterative updates). (PR #24)  
- Visualization: scenario comparison uses DataFrame with user-friendly headers; improved compare flow. (PR #16)  
- Visualization: handle empty scenario lists gracefully. (PR #26)  
- Inputs: use centralized config defaults in Streamlit widgets. (PR #9)  
- Inputs: updated validation for minimum monthly spending; allow zero monthly investment. (PRs #7, #25)
- Utils: hardened `get_bitcoin_price` with retries + jitter, session reuse, broader error handling, and warnings. (PRs #13, #18, #22)  
- Types/Docs: added type annotations and docstrings across modules. (PR #21)

### Fixed
- Minor README and setup instruction fixes. (PR #1)

### Performance
- Caching: use Streamlit cache for Bitcoin price; earlier timestamped caching approach explored. (commit `8a22999`, PR #4)  

---

## 2025-08-18
### Added
- Dependencies for data/HTTP (e.g., requests, pandas, plotly) recorded in `requirements.txt`. (PR #2)

### Changed
- Validation centralized into its own module.  
- Switched to timestamped cache for BTC price.  
- `main.py` passes a single cached BTC price into retirement calculations.  
- README setup improvements.

---

## 2025-08-17
### Project bootstrap
- Initial repository scaffolding and README.  
- Initial code commit and early README iterations/cleanup.  
- Dev container folder added; core files updated (`main.py`, `config.py`, `requirements.txt`).
