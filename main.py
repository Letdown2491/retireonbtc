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
)
from validation import validate_inputs
from config import (
    BITCOIN_GROWTH_RATE_OPTIONS,
    BITCOIN_PRICE_TTL,
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
)
from visualization import show_progress_visualization, show_fan_chart

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
    current_holdings: float,
    monthly_investment: float,
    current_bitcoin_price: float,
):
    return calculate_bitcoin_needed(
        monthly_spending,
        current_age,
        retirement_age,
        life_expectancy,
        bitcoin_growth_rate,
        inflation_rate,
        current_holdings,
        monthly_investment,
        current_bitcoin_price,
    )


@st.cache_data
def _cached_project_holdings_over_time(
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    bitcoin_growth_rate: float,
    inflation_rate: float,
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

            col4, col5 = st.columns(2)
            with col4:
                monthly_spending = st.text_input(
                    "Monthly Spending Needs (USD)",
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
                        returns = simulate_regime_shift_returns(years, n_sims, seed=seed)
                        pct, prob_not_run_out = simulate_percentiles_and_prob(
                            returns,
                            current_age=inputs["current_age"],
                            retirement_age=inputs["retirement_age"],
                            current_holdings=inputs["current_holdings"],
                            monthly_investment=inputs["monthly_investment"],
                            monthly_spending=inputs["monthly_spending"],
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
        current_holdings=inputs["current_holdings"],
        monthly_investment=inputs["monthly_investment"],
        monthly_spending=inputs["monthly_spending"],
        current_bitcoin_price=current_bitcoin_price,
    )

    score, details = health_score_from_outputs(
        projected_btc_at_retirement=total_bitcoin_holdings,
        btc_needed_at_retirement=bitcoin_needed,
        holdings_series_btc=holdings_series,
        current_age=inputs["current_age"],
        retirement_age=inputs["retirement_age"],
        life_expectancy=life_expectancy,
    )

    if total_bitcoin_holdings >= bitcoin_needed:
        result = (
            f"🎉 Great news! You're projected to retire in {years_until_retirement} years with ₿{total_bitcoin_holdings:.4f}. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f} in current dollar terms. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need ₿{bitcoin_needed:.4f} "
            f"(about ${total_retirement_expenses:,.2f} today). "
            f"By then, your contributions alone will total ₿{future_investment_value / future_bitcoin_price:.4f}. "
            f"The chart below displays your Bitcoin holdings for the next {life_expectancy - inputs['current_age']} years in orange, and your expenses denominated in Bitcoin in blue."
        )
    else:
        additional_bitcoin_needed = bitcoin_needed - total_bitcoin_holdings
        result = (
            f"🚨 You’ll need an additional ₿{additional_bitcoin_needed:.4f} to retire in {years_until_retirement} years. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f} in current dollar term. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need ₿{bitcoin_needed:.4f} "
            f"(about ${total_retirement_expenses:,.2f} today). "
            f"By then, your contributions alone will total ₿{future_investment_value / future_bitcoin_price:.4f}. "
            f"The chart below displays your Bitcoin holdings for the next {life_expectancy - inputs['current_age']} years in orange, and your expenses denominated in Bitcoin in blue."
        )
    st.write(result)
    show_progress_visualization(
        holdings_series,
        current_age=inputs["current_age"],
        monthly_spending=inputs["monthly_spending"],
        inflation_rate=inputs["inflation_rate"],
        current_bitcoin_price=current_bitcoin_price,
        bitcoin_growth_rate=inputs["bitcoin_growth_rate"],
    )
    
    if mc_results:
        prob_not_run_out = mc_results.get("prob_not_run_out")
        n_sims_msg = mc_results.get("n_sims")
        if prob_not_run_out is not None and n_sims_msg:
            st.info(
                f"Based on {n_sims_msg} Monte Carlo simulations, the probability that you will have enough Bitcoin to cover your expenses is {prob_not_run_out:.2%}."
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
        1) **What is your timeline?** The tool first figures out how many years you have until retirement and how long retirement is expected to last.
           - Years until retirement: `y = target_retirement_age - current_age`
           - Years in retirement: `n = life_expectancy - target_retirement_age`

        2) **What will your spending be at retirement?** We take today's monthly spending and grow it by inflation for `y` years, then annualize it.
           - `A = monthly_spending * 12 * (1 + r)^y`
             where `r` is the annual inflation rate.

        3) **How much will I spend across retirement?** We add up each retirement year's expenses, assuming they keep rising with inflation.
           - `Total_expenses = A * ((1 + r)^n - 1) / r * (1 + r)`
             where `n` is years in retirement.

        4) **What will Bitcoin's price be at retirement?** The calculator projects what one Bitcoin may cost at retirement by applying a user-specified growth rate.
           - `BTC_future_price = BTC_current_price * (1 + g)^y`
             where `g` is the annual BTC growth rate.

        5) **How many BTC would cover retirement expenses?** Dividing the total retirement expenses by the future Bitcoin price yields how many coins are needed.
           - `BTC_needed = Total_expenses / BTC_future_price`

        6) **If you invest monthly until retirement, how much will you hold??** If you invest every month, their future value is computed with monthly compounding.
           - `FV_contributions = P * ((1 + i)^(12y) - 1) / i * (1 + i)`
             where `P` is the monthly contribution and `i` is the monthly growth rate.

        7) **How much Bitcoin will you own including current holdings?** The future investment value is converted into Bitcoin using the projected price, then added to any coins you already own.
           - `BTC_from_investments = FV_contributions / BTC_future_price`
           - `BTC_total = current_BTC_holdings + BTC_from_investments`

        8) **Do you have enough Bitcoin to retire?**
           If `BTC_total >= BTC_needed`, your projected BTC covers inflation-adjusted retirement spending. Otherwise, you'll see the shortfall.
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
