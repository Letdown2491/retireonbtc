# main.py
import streamlit as st
import time
from utils import get_bitcoin_price, initialize_session_state
from calculations import (
    calculate_bitcoin_needed,
    project_holdings_over_time,
    health_score_from_outputs,
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
from visualization import show_progress_visualization


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
    with st.expander("Retirement Calculator", expanded=st.session_state.calculator_expanded):
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
                on_change=_on_input_change,
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
                on_change=_on_input_change,
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
                on_change=_on_input_change,
            )

        monthly_spending = st.number_input(
            "Monthly Spending Needs (USD)",
            min_value=1.0,
            value=st.session_state.get("monthly_spending", DEFAULT_MONTHLY_SPENDING),
            help="Your estimated monthly expenses in retirement",
            key="monthly_spending",
            on_change=_on_input_change,
        )

        bitcoin_growth_rate_label = st.selectbox(
            "Bitcoin Growth Rate Projection",
            list(BITCOIN_GROWTH_RATE_OPTIONS.keys()),
            index=0,
            key="bitcoin_growth_rate_label",
            on_change=_on_input_change,
        )
        bitcoin_growth_rate = BITCOIN_GROWTH_RATE_OPTIONS[bitcoin_growth_rate_label]

        inflation_rate = st.number_input(
            "Inflation Rate (%)",
            min_value=0.0,
            value=st.session_state.get("inflation_rate", DEFAULT_INFLATION_RATE),
            help="Expected annual inflation rate",
            key="inflation_rate",
            on_change=_on_input_change,
        )

        col6, col7 = st.columns(2)
        with col6:
            current_holdings = st.number_input(
                "Current Bitcoin Holdings",
                min_value=0.0,
                max_value=HOLDINGS_MAX,
                value=st.session_state.get("current_holdings", DEFAULT_CURRENT_HOLDINGS),
                help="How much Bitcoin you currently own",
                key="current_holdings",
                on_change=_on_input_change,
            )
        with col7:
            monthly_investment = st.number_input(
                "Monthly Recurring Investment (USD)",
                min_value=0.0,
                value=st.session_state.get("monthly_investment", DEFAULT_MONTHLY_INVESTMENT),
                help="How much you invest in Bitcoin each month",
                key="monthly_investment",
                on_change=_on_input_change,
            )

        if st.button("Calculate Retirement Plan"):
            inputs = {
                "current_age": current_age,
                "retirement_age": retirement_age,
                "life_expectancy": life_expectancy,
                "monthly_spending": monthly_spending,
                "bitcoin_growth_rate": bitcoin_growth_rate,
                "inflation_rate": inflation_rate,
                "current_holdings": current_holdings,
                "monthly_investment": monthly_investment,
            }
            errors = validate_form_inputs(inputs)
            if errors:
                for err in errors:
                    st.error(err)
                _on_input_change()
            else:
                plan, current_bitcoin_price = compute_retirement_plan(inputs)
                st.session_state.results_data = (plan, inputs, current_bitcoin_price)
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


def render_results(plan, inputs, current_bitcoin_price):
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
            f"Great news! You're projected to retire in {years_until_retirement} years with {total_bitcoin_holdings:.4f} BTC. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f}. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need {bitcoin_needed:.4f} BTC "
            f"(about ${total_retirement_expenses:,.2f}). "
            f"By then, your contributions alone will total {future_investment_value / future_bitcoin_price:.4f} BTC. "
            f"The chart below displays your BTC holdings over time for the next {life_expectancy - inputs['current_age']} years."
        )
    else:
        additional_bitcoin_needed = bitcoin_needed - total_bitcoin_holdings
        result = (
            f"You’ll need an additional {additional_bitcoin_needed:.4f} BTC to retire in {years_until_retirement} years. "
            f"At that time, your inflation-adjusted annual expenses are expected to be ${annual_expense_at_retirement:,.2f}. "
            f"\n\n"
            f"Your retirement health score is {score}/100 with a funding ratio of {details['funding_ratio']:.2f}x. "
            f"To fund {retirement_duration} years of retirement, you will need {bitcoin_needed:.4f} BTC "
            f"(about ${total_retirement_expenses:,.2f}). "
            f"By then, your contributions alone will total {future_investment_value / future_bitcoin_price:.4f} BTC. "
            f"The chart below displays your BTC holdings over time for the next {life_expectancy - inputs['current_age']} years."
        )
    st.write(result)

    show_progress_visualization(
        holdings_series,
        current_age=inputs["current_age"],
    )

    st.warning(
        "Note: Bitcoin prices are highly volatile. These calculations are estimates and should not be considered financial advice."
    )
    return score, details


def main():
    st.title("Bitcoin Retirement Calculator")
    initialize_session_state()
    if "cached_price" not in st.session_state:
        st.session_state["cached_price"] = cached_get_bitcoin_price(quick_fail=True)
        st.session_state["cached_price_timestamp"] = time.time()
    render_calculator()
    if st.session_state.get("results_available"):
        plan, inputs, current_bitcoin_price = st.session_state["results_data"]
        with st.expander("Retirement Summary", expanded=st.session_state.results_expanded):
            render_results(plan, inputs, current_bitcoin_price)


if __name__ == "__main__":
    main()
