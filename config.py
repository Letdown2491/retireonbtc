# config.py

# Default values
DEFAULT_CURRENT_AGE = 21
DEFAULT_RETIREMENT_AGE = 67
DEFAULT_LIFE_EXPECTANCY = 85
DEFAULT_MONTHLY_SPENDING = 5000.0
DEFAULT_BITCOIN_GROWTH_RATE = 21.0
DEFAULT_INFLATION_RATE = 5.0
DEFAULT_CURRENT_HOLDINGS = 0.1
DEFAULT_MONTHLY_INVESTMENT = 500.0
DEFAULT_TAX_RATE = 15.0

# Bitcoin growth rate options
BITCOIN_GROWTH_RATE_OPTIONS = {
    "Moderate (21%)": 21.0,
    "Conservative (10%)": 10.0,
    "Aggressive (30%)": 30.0,
    "Hyperbitcoinization (42%)": 42
}

# Input validation ranges
AGE_RANGE = (18, 120)
SPENDING_MIN = 1.0
RATE_MIN = 0.0
HOLDINGS_MAX = 21000000.0
TAX_RATE_MIN = 0.0
TAX_RATE_MAX = 60.0

# Caching and simulation defaults
BITCOIN_PRICE_TTL = 300  # seconds
SIM_FAST = 1000
SIM_ACCURATE = 10000
FAST_MODE_SEED = 42

# UI tuning constants
SPENDING_STEP = 100.0
INFLATION_STEP = 0.5
INFLATION_MAX = 100.0
HOLDINGS_STEP = 0.01
INVESTMENT_STEP = 50.0

# Optimizer settings
OPT_TARGET_PROB = 0.80
OPT_UPPER_TARGET_HINT = 0.90
OPT_SIMS_MIN = 5000
OPT_SEED = 12345
OPT_MAX_TOTAL_INVESTMENT = 500000.0  # cap on total monthly investment suggested
OPT_MAX_EXPENSE_CUT_PCT = 0.50     # up to 50% cut from baseline
OPT_MAX_RETIRE_DELAY_YEARS = 10    # no more than 10-year delay
OPT_GRANULARITY_DOLLARS = 10.0
OPT_GRANULARITY_YEARS = 1.0
OPT_ALTERNATE_COUNT = 1
OPT_WEIGHT_INVEST = 1.0
OPT_WEIGHT_EXPENSE = 1.0
OPT_WEIGHT_RETIRE_YEAR = 0.75

# Easing settings (when probability > 90%)
OPT_MAX_EXPENSE_INCREASE_PCT = 0.25

# Halving-anchored scenario configuration
HALVING_ANCHOR_YEAR = 2024
HALVING_ANCHOR_MONTH = 4
HALVING_ANCHOR_DAY = 20
HALVING_CYCLE_MONTHS = 48
# Phase parameters: (annual mean arithmetic return, annual volatility)
# Four 12-month phases: post-halving momentum, expansion, cooldown/winter, re-accumulation
HALVING_PHASE_PARAMS = (
    (0.80, 0.85),  # 0–12 months after halving (post-halving momentum)
    (0.35, 0.60),  # 12–24 months (continued expansion)
    (-0.20, 0.70), # 24–36 months (cooldown/winter)
    (0.12, 0.50),  # 36–48 months (pre-halving re-accumulation)
)
HALVING_MIN_RETURN = -0.99

# Diminishing-returns schedule (applies to both deterministic and MC)
# Per-year log-drift decays with horizon: mu_y = mu0 / (1 + y / PRICE_DECAY_YEARS_SCALE)
# where mu0 = ln(1 + user_growth_rate)
PRICE_DECAY_YEARS_SCALE = 42.0  # larger = slower decay; tune as needed
