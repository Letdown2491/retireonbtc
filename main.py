# main.py
import streamlit as st
import numpy as np
from utils import get_bitcoin_price, initialize_session_state
from calculations import (
    calculate_bitcoin_needed,
    project_holdings_over_time,
    health_score_from_outputs,
)
from simulation import (
    simulate_regime_shift_returns,
    simulate_percentiles_and_prob,
    generate_halving_returns,
)
from validation import validate_inputs
from config import (
    BITCOIN_GROWTH_RATE_OPTIONS,
    BITCOIN_PRICE_TTL,
    DEFAULT_TAX_RATE,
    DEFAULT_CURRENT_AGE,
    DEFAULT_RETIREMENT_AGE,
    DEFAULT_LIFE_EXPECTANCY,
    DEFAULT_MONTHLY_SPENDING,
    DEFAULT_INFLATION_RATE,
    DEFAULT_CURRENT_HOLDINGS,
    DEFAULT_MONTHLY_INVESTMENT,
    SPENDING_MIN,
    SPENDING_STEP,
    RATE_MIN,
    INFLATION_STEP,
    INFLATION_MAX,
    HOLDINGS_MAX,
    HOLDINGS_STEP,
    INVESTMENT_STEP,
    SIM_FAST,
    SIM_ACCURATE,
    FAST_MODE_SEED,
    AGE_RANGE,
    # Optimizer config
    OPT_TARGET_PROB,
    OPT_UPPER_TARGET_HINT,
    OPT_SIMS_MIN,
    OPT_SEED,
    OPT_MAX_TOTAL_INVESTMENT,
    OPT_MAX_EXPENSE_CUT_PCT,
    OPT_MAX_RETIRE_DELAY_YEARS,
    OPT_GRANULARITY_DOLLARS,
    OPT_GRANULARITY_YEARS,
    OPT_ALTERNATE_COUNT,
    OPT_WEIGHT_INVEST,
    OPT_WEIGHT_EXPENSE,
    OPT_WEIGHT_RETIRE_YEAR,
    OPT_MAX_EXPENSE_INCREASE_PCT,
)
from visualization import show_progress_visualization, show_fan_chart
from math import isfinite


def _round_dollars(x: float, step: int = 10) -> int:
    try:
        return int(step * round(float(x) / step))
    except Exception:
        return int(x)


def _fmt_money(x: float) -> str:
    """Format currency for markdown without triggering LaTeX parsing."""
    return f"\\${_round_dollars(x):,}"


def _recommend_adjustments(
    inputs: dict,
    current_bitcoin_price: float,
    baseline_prob: float,
    n_sims_used: int,
    target: float = OPT_TARGET_PROB,
) -> str:
    """Compute plain-English recommendations to reach a target success probability.

    Strategy: for each lever (increase monthly investment, delay retirement, cut
    monthly expenses), perform a bracket-and-bisect search for the minimal
    change that reaches the target probability using common random numbers for
    stability. If the baseline already meets the target band, provide context.
    """
    try:
        years = inputs["life_expectancy"] - inputs["current_age"] + 1
        # Use more sims for optimization for stability; keep a fixed seed.
        n_sims_opt = max(n_sims_used, OPT_SIMS_MIN)
        seed_opt = OPT_SEED
        opt_returns = generate_halving_returns(
            years,
            n_sims_opt,
            seed=seed_opt,
            target_arith_return_pct=float(inputs.get("bitcoin_growth_rate", 10.0)),
        )

        def eval_prob(
            monthly_investment_delta: float = 0.0,
            retirement_age_delta_years: int = 0,
            monthly_spending_delta: float = 0.0,
        ) -> float:
            # Clamp to valid ranges
            current_age = int(inputs["current_age"])
            retirement_age = int(inputs["retirement_age"]) + int(retirement_age_delta_years)
            life_expectancy = int(inputs["life_expectancy"])  # fixed
            # Ensure retirement_age < life_expectancy
            retirement_age = min(retirement_age, life_expectancy - 1)
            monthly_investment = max(0.0, float(inputs["monthly_investment"]) + float(monthly_investment_delta))
            monthly_spending = max(SPENDING_MIN, float(inputs["monthly_spending"]) - float(monthly_spending_delta))

            _, p = simulate_percentiles_and_prob(
                opt_returns,
                current_age=current_age,
                retirement_age=retirement_age,
                current_holdings=float(inputs["current_holdings"]),
                monthly_investment=monthly_investment,
                monthly_spending=monthly_spending,
                tax_rate=float(inputs.get("tax_rate", 0.0)),
                current_bitcoin_price=current_bitcoin_price,
            )
            return float(p)

        # Helper: monotone bracket + bisect to find minimal delta achieving target
        def bracket_and_bisect(
            getter,
            lower: float,
            upper_init: float,
            upper_cap: float,
            granularity: float,
        ) -> tuple[bool, float, float]:
            """Return (found, best_delta, prob) with minimal delta >= target.

            If not found within bounds, returns (False, upper_cap, last_prob).
            """
            p0 = getter(lower)
            if p0 >= target:
                return True, lower, p0
            # Expand to find an upper bracket
            upper = max(upper_init, lower + granularity)
            p_upper = getter(upper)
            while p_upper < target and upper < upper_cap:
                upper = min(upper * 2 if upper > 0 else granularity * 2, upper_cap)
                p_upper = getter(upper)
            if p_upper < target:
                return False, upper, p_upper
            # Bisect
            lo, hi = lower, upper
            best = upper
            best_p = p_upper
            while (hi - lo) > granularity:
                mid = (lo + hi) / 2
                mid = round(mid / granularity) * granularity
                pm = getter(mid)
                if pm >= target:
                    best, best_p = mid, pm
                    hi = mid
                else:
                    lo = mid
            return True, max(granularity, best), best_p

        current_prob_opt = eval_prob(0.0, 0, 0.0)

        # If already in the desired 80-90% band, keep it simple.
        if OPT_TARGET_PROB <= current_prob_opt <= OPT_UPPER_TARGET_HINT:
            return (
                "You’re already in the 80–90% target range, so no changes are needed. "
                "If you’d like a bit more cushion, a small increase in contributions or a modest expense trim can nudge the odds higher."
            )

        # Search parameters and caps
        base_invest = float(inputs["monthly_investment"])
        base_spend = float(inputs["monthly_spending"])
        base_retire = int(inputs["retirement_age"])
        current_age = int(inputs["current_age"])
        max_retire_years = max(
            0,
            min(
                OPT_MAX_RETIRE_DELAY_YEARS,
                AGE_RANGE[1] - 1 - base_retire,
                inputs["life_expectancy"] - 1 - base_retire,
            ),
        )

        # Monthly investment increase
        invest_cap_total = max(OPT_MAX_TOTAL_INVESTMENT, base_invest)
        invest_delta_cap = max(0.0, invest_cap_total - base_invest)
        def get_prob_invest(d: float) -> float:
            return eval_prob(monthly_investment_delta=d)
        found_i, best_i, prob_i = bracket_and_bisect(
            get_prob_invest,
            0.0,
            max(50.0, INVESTMENT_STEP),
            invest_delta_cap,
            OPT_GRANULARITY_DOLLARS,
        )

        # Retirement delay in years (integer steps)
        def get_prob_retire(dy: int) -> float:
            return eval_prob(retirement_age_delta_years=int(dy))
        # Convert to float delta for the search, but evaluate with int
        found_r, best_r_f, prob_r = bracket_and_bisect(
            lambda x: get_prob_retire(int(round(x))),
            0.0,
            1.0,
            float(max_retire_years),
            OPT_GRANULARITY_YEARS,
        )
        best_r = int(round(best_r_f))

        # Monthly expense cut
        spend_delta_cap = max(0.0, min(base_spend * OPT_MAX_EXPENSE_CUT_PCT, base_spend - SPENDING_MIN))
        def get_prob_spend(d: float) -> float:
            return eval_prob(monthly_spending_delta=d)
        found_s, best_s, prob_s = bracket_and_bisect(
            get_prob_spend,
            0.0,
            max(50.0, SPENDING_STEP),
            spend_delta_cap,
            OPT_GRANULARITY_DOLLARS,
        )

        # Collect feasible options
        options: list[tuple[str, float, str]] = []  # (key, normalized_cost, text)

        if found_i and isfinite(best_i) and best_i > 0:
            norm = OPT_WEIGHT_INVEST * (best_i / max(base_invest, 1.0))
            text = f"increasing your monthly investment by about {_fmt_money(best_i)}"
            options.append(("invest", norm, text))
        if found_r and best_r > 0:
            horizon = max(1, inputs["retirement_age"] - current_age)
            norm = OPT_WEIGHT_RETIRE_YEAR * (best_r / horizon)
            years_word = "year" if best_r == 1 else "years"
            text = f"delaying retirement by roughly {best_r} {years_word}"
            options.append(("retire", norm, text))
        if found_s and isfinite(best_s) and best_s > 0:
            norm = OPT_WEIGHT_EXPENSE * (best_s / max(base_spend, 1.0))
            text = f"cutting monthly expenses by about {_fmt_money(best_s)}"
            options.append(("spend", norm, text))

        # If baseline is comfortably above range (e.g., >90%), suggest easing amounts
        if current_prob_opt > OPT_UPPER_TARGET_HINT:
            # Find maximum reduction in invest, maximum retirement advance, and maximum increase in expenses
            def ease_bracket_and_bisect(getter, upper_init: float, upper_cap: float, granularity: float) -> float:
                """Return the largest magnitude m such that prob >= target."""
                lo = 0.0
                hi = max(upper_init, granularity)
                # Expand until just below target or hit cap
                p_hi = getter(hi)
                while p_hi >= target and hi < upper_cap:
                    lo = hi
                    hi = min(hi * 2, upper_cap)
                    p_hi = getter(hi)
                # If even minimal change drops below target, stick with lo (could be 0)
                if p_hi < target and lo == 0.0:
                    return 0.0
                # Bisect to the boundary from above
                left, right = lo, hi
                best = lo
                while (right - left) > granularity:
                    mid = (left + right) / 2
                    mid = round(mid / granularity) * granularity
                    pm = getter(mid)
                    if pm >= target:
                        best = mid
                        left = mid
                    else:
                        right = mid
                return max(0.0, best)

            # Reduce monthly investment by m (cannot go below 0)
            invest_reduce_cap = float(base_invest)
            def ease_invest(m: float) -> float:
                return eval_prob(monthly_investment_delta=-float(m))
            max_ease_invest = ease_bracket_and_bisect(
                ease_invest, max(50.0, INVESTMENT_STEP), invest_reduce_cap, OPT_GRANULARITY_DOLLARS
            )

            # Bring retirement forward by y years (cannot be <= current_age)
            max_advance_years = max(0, base_retire - (current_age + 1))
            def ease_retire(m: float) -> float:
                return eval_prob(retirement_age_delta_years=-int(round(m)))
            max_ease_retire_years = 0
            if max_advance_years > 0:
                max_ease_retire_years = int(round(ease_bracket_and_bisect(
                    ease_retire, 1.0, float(max_advance_years), OPT_GRANULARITY_YEARS
                )))

            # Allow monthly expense increase by m (up to a cap)
            spend_increase_cap = float(base_spend * OPT_MAX_EXPENSE_INCREASE_PCT)
            def ease_spend(m: float) -> float:
                return eval_prob(monthly_spending_delta=-float(m))
            max_ease_spend = ease_bracket_and_bisect(
                ease_spend, max(50.0, SPENDING_STEP), spend_increase_cap, OPT_GRANULARITY_DOLLARS
            )

            phrases = []
            if max_ease_invest > 0:
                phrases.append(f"reduce monthly investment by about {_fmt_money(max_ease_invest)}")
            if max_ease_retire_years > 0:
                years_word = "year" if max_ease_retire_years == 1 else "years"
                phrases.append(f"bring retirement forward by around {max_ease_retire_years} {years_word}")
            if max_ease_spend > 0:
                phrases.append(f"increase monthly expenses by about {_fmt_money(max_ease_spend)}")

            if not phrases:
                return (
                    "You’re comfortably above the 80–90% target. You could scale back slightly and still maintain at least an 80% chance of success."
                )

            if len(phrases) == 1:
                actions = phrases[0]
            elif len(phrases) == 2:
                actions = f"{phrases[0]} or {phrases[1]}"
            else:
                actions = f"{phrases[0]}, {phrases[1]}, or {phrases[2]}"

            return (
                f"You’re comfortably above the 80–90% target. You could {actions} and still maintain at least an 80% chance of success."
            )

        # If below target and no single lever suffices, suggest combining levers
        if current_prob_opt < target and not options:
            # Try simple combinations: small retirement delays plus investment or expense changes
            best_combo_text = None
            best_combo_norm = float("inf")
            for dy in range(1, int(max_retire_years) + 1):
                # Find minimal invest delta conditional on dy
                def get_prob_combo_invest(d: float, dy_local=dy) -> float:
                    return eval_prob(monthly_investment_delta=d, retirement_age_delta_years=dy_local)
                ci_found, ci_best, _ = bracket_and_bisect(
                    lambda d: get_prob_combo_invest(d),
                    0.0,
                    max(50.0, INVESTMENT_STEP),
                    invest_delta_cap,
                    OPT_GRANULARITY_DOLLARS,
                )
                if ci_found and ci_best > 0:
                    norm = (ci_best / max(base_invest, 1.0)) + (dy / max(1, inputs["retirement_age"] - current_age))
                    text = (
                        f"a blend of delaying retirement by about {dy} {'year' if dy == 1 else 'years'} "
                        f"and increasing monthly investment by roughly {_fmt_money(ci_best)}"
                    )
                    if norm < best_combo_norm:
                        best_combo_norm, best_combo_text = norm, text

                # Find minimal expense cut conditional on dy
                def get_prob_combo_spend(d: float, dy_local=dy) -> float:
                    return eval_prob(monthly_spending_delta=d, retirement_age_delta_years=dy_local)
                cs_found, cs_best, _ = bracket_and_bisect(
                    lambda d: get_prob_combo_spend(d),
                    0.0,
                    max(50.0, SPENDING_STEP),
                    spend_delta_cap,
                    OPT_GRANULARITY_DOLLARS,
                )
                if cs_found and cs_best > 0:
                    norm = (cs_best / max(base_spend, 1.0)) + (dy / max(1, inputs["retirement_age"] - current_age))
                    text = (
                        f"a blend of delaying retirement by about {dy} {'year' if dy == 1 else 'years'} "
                        f"and cutting monthly expenses by roughly {_fmt_money(cs_best)}"
                    )
                    if norm < best_combo_norm:
                        best_combo_norm, best_combo_text = norm, text

            if best_combo_text:
                return (
                    f"To reach at least an 80% chance of success, consider {best_combo_text}."
                )
            else:
                return (
                    "Reaching an 80% success probability within reasonable bounds wasn't feasible in these simulations. "
                    "A more substantial combination of delaying retirement, increasing contributions, and lowering expenses may be required."
                )

        # Pick the lowest normalized cost option as the primary recommendation
        if options:
            options.sort(key=lambda x: x[1])
            primary = options[0][2]
            # Offer brief alternates if available
            alternates = [opt[2] for opt in options[1:1+OPT_ALTERNATE_COUNT]]
            if alternates:
                return (
                    f"To reach at least an 80% chance of success, {primary} achieves the target. "
                    f"If you prefer a different path, {alternates[0]} also works."
                )
            else:
                return (
                    f"To reach at least an 80% chance of success, {primary} achieves the target."
                )

        # Fallback generic message
        return (
            "To improve your odds toward the 80% target, modest adjustments across contributions, retirement timing, or spending will help."
        )

    except Exception:
        # Fail silently with no recommendation if something unexpected happens
        return ""

st.set_page_config(
   page_title="Retire On BTC | Dashboard",  # <title> tag
   page_icon="📈",                           # emoji or path to an image
   # layout="wide",
   initial_sidebar_state="expanded",
)

st.markdown("""
  <style>
    /* Hide the entire top toolbar (hamburger + Deploy) */
    header {visibility: hidden;}
    /* Extra-safe: hide the toolbar container if present */
    [data-testid="stToolbar"] {visibility: hidden; height: 0; position: fixed;}
    /* Hide footer ("Made with Streamlit" etc.) */
    footer {visibility: hidden;}
  </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=BITCOIN_PRICE_TTL)
# Cache the Bitcoin price for 5 minutes to reduce API calls
def cached_get_bitcoin_price(quick_fail: bool = False):
    """Fetch and cache the current Bitcoin price for five minutes.

    Args:
        quick_fail (bool): If ``True``, fail fast and return the fallback price
            immediately on any API error.

    Returns:
        tuple: (price, warnings) returned from ``get_bitcoin_price``
    """
    return get_bitcoin_price(quick_fail=quick_fail)


def _on_input_change():
    st.session_state.calculator_expanded = True
    st.session_state.results_expanded = False
    st.session_state.results_available = False


@st.cache_data
def _cached_calculate_bitcoin_needed(
    monthly_spending: float,
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    bitcoin_growth_rate: float,
    inflation_rate: float,
    tax_rate: float,
    current_holdings: float,
    monthly_investment: float,
    current_bitcoin_price: float,
):
    return calculate_bitcoin_needed(
        monthly_spending=monthly_spending,
        current_age=current_age,
        retirement_age=retirement_age,
        life_expectancy=life_expectancy,
        bitcoin_growth_rate=bitcoin_growth_rate,
        inflation_rate=inflation_rate,
        current_holdings=current_holdings,
        monthly_investment=monthly_investment,
        current_bitcoin_price=current_bitcoin_price,
        tax_rate=tax_rate,
    )


@st.cache_data
def _cached_project_holdings_over_time(
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    bitcoin_growth_rate: float,
    inflation_rate: float,
    tax_rate: float,
    current_holdings: float,
    monthly_investment: float,
    monthly_spending: float,
    current_bitcoin_price: float,
):
    return project_holdings_over_time(
        current_age=current_age,
        retirement_age=retirement_age,
        life_expectancy=life_expectancy,
        bitcoin_growth_rate=bitcoin_growth_rate,
        inflation_rate=inflation_rate,
        tax_rate=tax_rate,
        current_holdings=current_holdings,
        monthly_investment=monthly_investment,
        monthly_spending=monthly_spending,
        current_bitcoin_price=current_bitcoin_price,
    )


def render_calculator():
    with st.expander("🧮 Retirement Calculator", expanded=st.session_state.calculator_expanded):
        with st.form("calculator_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                current_age = st.number_input(
                    "Current Age",
                    min_value=AGE_RANGE[0],
                    max_value=AGE_RANGE[1],
                    value=st.session_state.get("current_age", DEFAULT_CURRENT_AGE),
                    step=1,
                    help="Your current age in years",
                    key="current_age",
                )
            with col2:
                retirement_age = st.number_input(
                    "Retirement Age",
                    min_value=max(int(current_age) + 1, AGE_RANGE[0]),
                    max_value=AGE_RANGE[1],
                    value=st.session_state.get("retirement_age", DEFAULT_RETIREMENT_AGE),
                    step=1,
                    help="The age at which you plan to retire",
                    key="retirement_age",
                )
            with col3:
                life_expectancy = st.number_input(
                    "Life Expectancy",
                    min_value=max(int(retirement_age) + 1, AGE_RANGE[0]),
                    max_value=AGE_RANGE[1],
                    value=st.session_state.get("life_expectancy", DEFAULT_LIFE_EXPECTANCY),
                    step=1,
                    help="Your expected lifespan in years",
                    key="life_expectancy",
                )

            col4, col5, col6 = st.columns(3)
            with col4:
                monthly_spending = st.text_input(
                    "Monthly Spending (USD)",
                    value=str(
                        st.session_state.get(
                            "monthly_spending", DEFAULT_MONTHLY_SPENDING
                        )
                    ),
                    help="Your estimated monthly expenses in retirement",
                    key="monthly_spending",
                )

            with col5:
                inflation_rate = st.text_input(
                    "Inflation Rate (%)",
                    value=str(
                        st.session_state.get(
                            "inflation_rate", DEFAULT_INFLATION_RATE
                        )
                    ),
                    help="Expected annual inflation rate",
                    key="inflation_rate",
                )

            with col6:
                tax_rate = st.text_input(
                    "Tax on Withdrawals (%)",
                    value=str(
                        st.session_state.get(
                            "tax_rate", DEFAULT_TAX_RATE
                        )
                    ),
                    help="Flat tax applied when selling BTC to fund retirement spending",
                    key="tax_rate",
                )

            col6, col7 = st.columns(2)
            with col6:
                current_holdings = st.text_input(
                    "Current Bitcoin Holdings (₿)",
                    value=str(
                        st.session_state.get(
                            "current_holdings", DEFAULT_CURRENT_HOLDINGS
                        )
                    ),
                    help="How much Bitcoin you currently own",
                    key="current_holdings",
                )
            with col7:
                monthly_investment = st.text_input(
                    "Monthly Recurring Investment (USD)",
                    value=str(
                        st.session_state.get(
                            "monthly_investment", DEFAULT_MONTHLY_INVESTMENT
                        )
                    ),
                    help="How much you invest in Bitcoin each month",
                    key="monthly_investment",
                )

            col8, col9 = st.columns(2)
            with col8:
                bitcoin_growth_rate_label = st.selectbox(
                    "Bitcoin Growth Rate Projection",
                    list(BITCOIN_GROWTH_RATE_OPTIONS.keys()),
                    index=0,
                    key="bitcoin_growth_rate_label",
                )
                bitcoin_growth_rate = BITCOIN_GROWTH_RATE_OPTIONS[bitcoin_growth_rate_label]

            with col9:
                simulation_mode = st.selectbox(
                    "Monte Carlo Simulation Mode",
                    ["Fast", "Accurate"],
                    index=0,
                    key="simulation_mode",
                    help=f"Fast = {SIM_FAST} simulations, Accurate = {SIM_ACCURATE} simulations",
                )

            submitted = st.form_submit_button("🧮 Calculate Retirement Plan")
            if submitted:
                _on_input_change()

                parse_errors = []

                def _to_float(value: str, field: str):
                    if value is None or value.strip() == "":
                        parse_errors.append(f"{field} is required.")
                        return None
                    try:
                        return float(value)
                    except ValueError:
                        parse_errors.append(f"{field} must be a valid number.")
                        return None

                monthly_spending_val = _to_float(monthly_spending, "Monthly Spending")
                inflation_rate_val = _to_float(inflation_rate, "Inflation Rate")
                tax_rate_val = _to_float(tax_rate, "Tax on Withdrawals")
                current_holdings_val = _to_float(current_holdings, "Current Bitcoin Holdings")
                monthly_investment_val = _to_float(monthly_investment, "Monthly Recurring Investment")

                if parse_errors:
                    for err in parse_errors:
                        st.error(err)
                else:
                    inputs = {
                        "current_age": current_age,
                        "retirement_age": retirement_age,
                        "life_expectancy": life_expectancy,
                        "monthly_spending": monthly_spending_val,
                        "bitcoin_growth_rate": bitcoin_growth_rate,
                        "inflation_rate": inflation_rate_val,
                        "current_holdings": current_holdings_val,
                        "monthly_investment": monthly_investment_val,
                        "tax_rate": tax_rate_val,
                        "simulation_mode": simulation_mode,
                    }
                    errors = validate_form_inputs(inputs)
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        plan, current_bitcoin_price = compute_retirement_plan(inputs)
                        years = inputs["life_expectancy"] - inputs["current_age"] + 1
                        n_sims = (1000 if simulation_mode == "Fast" else 10000)
                        seed = (42 if simulation_mode == "Fast" else None)
                        returns = generate_halving_returns(
                            years,
                            n_sims,
                            seed=seed,
                            target_arith_return_pct=float(inputs.get("bitcoin_growth_rate", 10.0)),
                        )
                        pct, prob_not_run_out = simulate_percentiles_and_prob(
                            returns,
                            current_age=inputs["current_age"],
                            retirement_age=inputs["retirement_age"],
                            current_holdings=inputs["current_holdings"],
                            monthly_investment=inputs["monthly_investment"],
                            monthly_spending=inputs["monthly_spending"],
                            tax_rate=inputs["tax_rate"],
                            current_bitcoin_price=current_bitcoin_price,
                        )
                        mc_results = {
                            "percentiles": pct,
                            "prob_not_run_out": prob_not_run_out,
                            "n_sims": n_sims,
                        }
                        st.session_state.results_data = (
                            plan,
                            inputs,
                            current_bitcoin_price,
                            mc_results,
                        )
                        st.session_state.results_available = True
                        st.session_state.results_expanded = True
                        st.session_state.calculator_expanded = False
                        # Rerun so the updated expander states take effect immediately
                        st.rerun()


def validate_form_inputs(inputs):
    return validate_inputs(
        inputs["current_age"],
        inputs["retirement_age"],
        inputs["life_expectancy"],
        inputs["monthly_spending"],
        inputs["bitcoin_growth_rate"],
        inputs["inflation_rate"],
        inputs["current_holdings"],
        inputs["monthly_investment"],
        inputs["tax_rate"],
    )


def compute_retirement_plan(inputs):
    with st.spinner("Calculating your retirement plan..."):
        st.session_state.last_inputs = inputs

        # Use Streamlit's cache directly; avoid manual TTL in session state
        current_bitcoin_price, price_warnings = cached_get_bitcoin_price(quick_fail=True)
        for warning_msg in price_warnings:
            st.warning(warning_msg)

        plan = _cached_calculate_bitcoin_needed(
            inputs["monthly_spending"],
            inputs["current_age"],
            inputs["retirement_age"],
            inputs["life_expectancy"],
            inputs["bitcoin_growth_rate"],
            inputs["inflation_rate"],
            inputs["tax_rate"],
            inputs["current_holdings"],
            inputs["monthly_investment"],
            current_bitcoin_price,
        )
    return plan, current_bitcoin_price


def render_results(plan, inputs, current_bitcoin_price, mc_results=None):
    """Render the retirement plan results and return a health score."""

    bitcoin_needed = plan.bitcoin_needed
    life_expectancy = plan.life_expectancy
    total_bitcoin_holdings = plan.total_bitcoin_holdings
    future_investment_value = plan.future_investment_value
    annual_expense_at_retirement = plan.annual_expense_at_retirement
    future_bitcoin_price = plan.future_bitcoin_price
    total_retirement_expenses = plan.total_retirement_expenses

    years_until_retirement = inputs["retirement_age"] - inputs["current_age"]
    retirement_duration = life_expectancy - inputs["retirement_age"]

    holdings_series = _cached_project_holdings_over_time(
        current_age=inputs["current_age"],
        retirement_age=inputs["retirement_age"],
        life_expectancy=life_expectancy,
        bitcoin_growth_rate=inputs["bitcoin_growth_rate"],
        inflation_rate=inputs["inflation_rate"],
        tax_rate=float(inputs.get("tax_rate", 0.0)),
        current_holdings=inputs["current_holdings"],
        monthly_investment=inputs["monthly_investment"],
        monthly_spending=inputs["monthly_spending"],
        current_bitcoin_price=current_bitcoin_price,
    )

    # Use the chart's series as the source of truth for holdings at retirement
    holdings_at_retirement = float(holdings_series[years_until_retirement]) if years_until_retirement >= 0 else float(total_bitcoin_holdings)

    # Recompute required BTC across retirement using the same logic/shapes as the chart
    try:
        growth_multiplier = 1 + float(inputs["bitcoin_growth_rate"]) / 100.0
        inflation_multiplier = 1 + float(inputs["inflation_rate"]) / 100.0
        retirement_years_idx = np.arange(years_until_retirement, years_until_retirement + retirement_duration)
        projected_prices_chart = current_bitcoin_price * (growth_multiplier ** retirement_years_idx)
        gross = 1.0 / max(1e-6, 1.0 - float(inputs.get("tax_rate", 0.0)) / 100.0)
        yearly_expenses_chart = float(inputs["monthly_spending"]) * 12.0 * (inflation_multiplier ** retirement_years_idx) * gross
        bitcoin_needed_chart = float(np.sum(yearly_expenses_chart / projected_prices_chart)) if retirement_years_idx.size else 0.0
    except Exception:
        bitcoin_needed_chart = bitcoin_needed

    score, details = health_score_from_outputs(
        projected_btc_at_retirement=holdings_at_retirement,
        btc_needed_at_retirement=bitcoin_needed_chart,
        holdings_series_btc=holdings_series,
        current_age=inputs["current_age"],
        retirement_age=inputs["retirement_age"],
        life_expectancy=life_expectancy,
    )

    # Derive contributions in BTC from the chart for consistency
    contributions_btc = max(holdings_at_retirement - float(inputs["current_holdings"]), 0.0)

    if holdings_at_retirement >= bitcoin_needed_chart:
        result = (
            f"🎉 Great news! You're projected to retire in {years_until_retirement} years with ₿{holdings_at_retirement:.4f}. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f} in current dollar terms. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need ₿{bitcoin_needed_chart:.4f} "
            f"(about ${total_retirement_expenses:,.2f} today). "
            f"By then, your contributions alone will total ₿{contributions_btc:.4f}. "
            f"The chart below displays your Bitcoin holdings for the next {life_expectancy - inputs['current_age']} years."
        )
    else:
        additional_bitcoin_needed = bitcoin_needed_chart - holdings_at_retirement
        result = (
            f"🚨 You’ll need an additional ₿{additional_bitcoin_needed:.4f} to retire in {years_until_retirement} years. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f} in current dollar term. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need ₿{bitcoin_needed_chart:.4f} "
            f"(about ${total_retirement_expenses:,.2f} today). "
            f"By then, your contributions alone will total ₿{contributions_btc:.4f}. "
            f"The chart below displays your Bitcoin holdings for the next {life_expectancy - inputs['current_age']} years."
        )
    st.write(result)
    show_progress_visualization(
        holdings_series,
        current_age=inputs["current_age"],
        monthly_spending=inputs["monthly_spending"],
        inflation_rate=inputs["inflation_rate"],
        tax_rate=float(inputs.get("tax_rate", 0.0)),
        current_bitcoin_price=current_bitcoin_price,
        bitcoin_growth_rate=inputs["bitcoin_growth_rate"],
    )
    
    if mc_results:
        prob_not_run_out = mc_results.get("prob_not_run_out")
        n_sims_msg = mc_results.get("n_sims")
        if prob_not_run_out is not None and n_sims_msg:
            reco_text = _recommend_adjustments(
                inputs,
                current_bitcoin_price,
                baseline_prob=float(prob_not_run_out),
                n_sims_used=int(n_sims_msg),
            )
            if reco_text:
                st.write(
                    f"Based on {n_sims_msg} Monte Carlo simulations, your probability of success is {prob_not_run_out:.2%}. {reco_text}"
                )
            else:
                st.write(
                    f"Based on {n_sims_msg} Monte Carlo simulations, your probability of success is {prob_not_run_out:.2%}."
                )
        percentiles = mc_results.get("percentiles")
        paths = mc_results.get("paths")
        if percentiles is not None:
            show_fan_chart(percentiles, inputs["current_age"])
        elif paths is not None:
            show_fan_chart(paths, inputs["current_age"])

    st.info(
        "Note: Bitcoin prices are highly volatile. These calculations are estimates and should not be considered financial advice."
    )
    return score, details

def render_calculation_methodology():
    st.markdown(
        """
        1) **Timeline**: We compute years until retirement and the years in retirement.
           - Until retirement: `y = retirement_age - current_age`
           - In retirement: `n = life_expectancy - retirement_age`

        2) **Inflation and expenses**: Today’s monthly spending is grown by inflation to retirement, then across retirement.
           - At retirement: `A = monthly_spending * 12 * (1 + r)^y`
           - Across retirement: `Total_expenses = A * ((1 + r)^n - 1) / r * (1 + r)`
             where `r` is the annual inflation rate.

        3) **Deterministic price path (calculator + chart)**: For the calculator and the orange/blue chart, BTC price is projected with a constant annual growth rate `g` from the slider.
           - Year `t` price: `P_t = BTC_current_price * (1 + g)^t`
           - Retirement price: `P_y = BTC_current_price * (1 + g)^y`

        4) **BTC needed across retirement (chart-consistent)**: Each retirement year’s expenses (in USD) are grossed up for taxes and divided by that year’s projected price and summed.
           - Gross-up factor `gross = 1 / (1 - τ)` where `τ` is the withdrawal tax rate (0–60%).
           - `BTC_needed_chart = Σ_{t=y}^{y+n-1} ((monthly_spending * 12 * (1 + r)^t) * gross) / (BTC_current_price * (1 + g)^t)`
           - Tax applies only to withdrawals used for spending; contributions/buys are not taxed in this model. The “Total retirement expenses” figure shown remains pre‑tax household expenses; gross‑up affects BTC needed and holdings.

        5) **Holdings over time (chart)**: Each pre‑retirement year converts that year’s USD contributions to BTC using that year’s projected price; post‑retirement years deduct inflated expenses in BTC grossed up for taxes.
           - Holdings series is what the chart shows; the “BTC at retirement” headline uses the holdings value at age `retirement_age`.
           - “Contributions alone” equals holdings at retirement minus current BTC holdings (so it never exceeds holdings).

        6) **Health score**: Uses the chart‑consistent “BTC at retirement” and “BTC needed” to compute funding ratio and runway. The funding ratio is `BTC_at_retirement / BTC_needed_chart`.

        7) **Monte Carlo (probability view)**: Separate from the calculator, MC simulates year‑by‑year log‑returns with two features:
           - Halving‑anchored cycle: post‑halving momentum, mid‑cycle cooldown, pre‑halving accumulation.
           - Geometric alignment and diminishing returns: long‑run CAGR matches your growth rate setting, but drift decays over longer horizons. We keep volatility phase‑aware.
           We then stream p10/p25/p50 percentiles of USD portfolio value and compute the probability of not running out of BTC during retirement.

        8) **Recommendations**: If probability is below 80%, we search for the minimal change to reach ≥80% (increase contributions, delay retirement, or cut spending). If it’s above 90%, we suggest concrete easing amounts that maintain ≥80%.
        """
)

def main():
    st.markdown(
        "<h1 style='margin: -4rem 0rem -2rem -0.5rem;'>📈 Retire On BTC</h1>",
        unsafe_allow_html=True,
    )
    initialize_session_state()
    price, _msgs = cached_get_bitcoin_price(quick_fail=True)
    st.markdown(
        f"**Current Bitcoin Price:** \\${float(price):,.2f}"
    )
    render_calculator()
    if st.session_state.get("results_available"):
        plan, inputs, current_bitcoin_price, mc_results = st.session_state["results_data"]
        with st.expander("📆 Retirement Summary", expanded=st.session_state.results_expanded):
            render_results(plan, inputs, current_bitcoin_price, mc_results)
    with st.expander("🛠️ Calculation Methodology"):
            render_calculation_methodology()


if __name__ == "__main__":
    main()
