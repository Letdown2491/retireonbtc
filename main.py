# main.py
import streamlit as st
import time
from datetime import datetime
from utils import get_bitcoin_price, initialize_session_state
from calculations import (
    calculate_bitcoin_needed,
    project_holdings_over_time,
    health_score_from_outputs,
)
from simulation import (
    simulate_regime_shift_returns,
    simulate_holdings_paths,
)
from validation import validate_inputs
from config import (
    BITCOIN_GROWTH_RATE_OPTIONS,
    DEFAULT_CURRENT_AGE,
    DEFAULT_RETIREMENT_AGE,
    DEFAULT_LIFE_EXPECTANCY,
    DEFAULT_MONTHLY_SPENDING,
    DEFAULT_INFLATION_RATE,
    DEFAULT_CURRENT_HOLDINGS,
    DEFAULT_MONTHLY_INVESTMENT,
    HOLDINGS_MAX,
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

BITCOIN_PRICE_TTL = 300


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
                monthly_spending = st.number_input(
                    "Monthly Spending Needs (USD)",
                    min_value=1.0,
                    value=st.session_state.get("monthly_spending", DEFAULT_MONTHLY_SPENDING),
                    step=0.01,
                    format="%.2f",
                    help="Your estimated monthly expenses in retirement",
                    key="monthly_spending",
                )

            with col5:
                inflation_rate = st.number_input(
                    "Inflation Rate (%)",
                    min_value=0.0,
                    value=st.session_state.get("inflation_rate", DEFAULT_INFLATION_RATE),
                    step=0.01,
                    format="%.2f",
                    help="Expected annual inflation rate",
                    key="inflation_rate",
                )

            col6, col7 = st.columns(2)
            with col6:
                current_holdings = st.number_input(
                    "Current Bitcoin Holdings (₿)",
                    min_value=0.0,
                    max_value=HOLDINGS_MAX,
                    value=st.session_state.get("current_holdings", DEFAULT_CURRENT_HOLDINGS),
                    step=0.00000001,
                    format="%.8f",
                    help="How much Bitcoin you currently own",
                    key="current_holdings",
                )
            with col7:
                monthly_investment = st.number_input(
                    "Monthly Recurring Investment (USD)",
                    min_value=0.0,
                    value=st.session_state.get("monthly_investment", DEFAULT_MONTHLY_INVESTMENT),
                    step=0.01,
                    format="%.2f",
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
                num_simulations = st.number_input(
                    "Number of Monte Carlo Simulations",
                    min_value=1,
                    max_value=10000,
                    step=100,
                    value=st.session_state.get("num_simulations", 1000),
                    key="num_simulations",
                )

            submitted = st.form_submit_button("🧮 Calculate Retirement Plan")
            if submitted:
                _on_input_change()
                inputs = {
                    "current_age": current_age,
                    "retirement_age": retirement_age,
                    "life_expectancy": life_expectancy,
                    "monthly_spending": monthly_spending,
                    "bitcoin_growth_rate": bitcoin_growth_rate,
                    "inflation_rate": inflation_rate,
                    "current_holdings": current_holdings,
                    "monthly_investment": monthly_investment,
                    "num_simulations": int(num_simulations),
                }
                errors = validate_form_inputs(inputs)
                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    plan, current_bitcoin_price = compute_retirement_plan(inputs)
                    mc_results = None
                    years = inputs["life_expectancy"] - inputs["current_age"] + 1
                    returns = simulate_regime_shift_returns(years, int(num_simulations))
                    paths, prob_not_run_out = simulate_holdings_paths(
                        returns,
                        current_age=inputs["current_age"],
                        retirement_age=inputs["retirement_age"],
                        current_holdings=inputs["current_holdings"],
                        monthly_investment=inputs["monthly_investment"],
                        monthly_spending=inputs["monthly_spending"],
                        current_bitcoin_price=current_bitcoin_price,
                    )
                    mc_results = {
                        "paths": paths,
                        "prob_not_run_out": prob_not_run_out,
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

        refresh_needed = (
            "cached_price" not in st.session_state
            or "cached_price_timestamp" not in st.session_state
            or time.time() - st.session_state["cached_price_timestamp"] > BITCOIN_PRICE_TTL
        )
        if refresh_needed:
            st.session_state["cached_price"] = cached_get_bitcoin_price(quick_fail=True)
            st.session_state["cached_price_timestamp"] = time.time()

        current_bitcoin_price, price_warnings = st.session_state["cached_price"]
        for warning_msg in price_warnings:
            st.warning(warning_msg)

        plan = calculate_bitcoin_needed(
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

    holdings_series = project_holdings_over_time(
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
        if prob_not_run_out is not None:
            f"Based on the Monte Carlo simulations, the probability that you will have enough Bitcoin to cover your expenses is {prob_not_run_out:.2%}."
        paths = mc_results.get("paths")
        if paths is not None:
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
    if "cached_price" not in st.session_state:
        st.session_state["cached_price"] = cached_get_bitcoin_price(quick_fail=True)
        st.session_state["cached_price_timestamp"] = time.time()
    price, _msgs = st.session_state["cached_price"]
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
