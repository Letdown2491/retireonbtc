# main.py
import streamlit as st
from utils import get_bitcoin_price, initialize_session_state
from calculations import calculate_bitcoin_needed
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
)

@st.cache_data(ttl=300)
def cached_get_bitcoin_price():
    """Fetch and cache the current Bitcoin price for five minutes.

    Returns:
        tuple: (price, warnings) returned from ``get_bitcoin_price``
    """
    return get_bitcoin_price()

def main():
    st.title("Bitcoin Retirement Calculator")

    # Initialize session state
    initialize_session_state()

    # Create a container for the form and buttons
    form_container = st.container()

    with form_container:
        # Create a form for better organization
        with st.form("retirement_form"):
            st.subheader("Personal Information")

            col1, col2, col3 = st.columns(3)
            with col1:
                current_age = st.number_input(
                    "Current Age",
                    min_value=18,
                    max_value=120,
                    value=DEFAULT_CURRENT_AGE,
                    step=1,
                    help="Your current age in years"
                )
            with col2:
                retirement_age = st.number_input(
                    "Retirement Age",
                    min_value=int(current_age)+1,
                    max_value=120,
                    value=DEFAULT_RETIREMENT_AGE,
                    step=1,
                    help="The age at which you plan to retire"
                )
            with col3:
                life_expectancy = st.number_input(
                    "Life Expectancy",
                    min_value=int(retirement_age)+1,
                    max_value=120,
                    value=DEFAULT_LIFE_EXPECTANCY,
                    step=1,
                    help="Your expected lifespan in years"
                )

            st.subheader("Financial Information")
            monthly_spending = st.number_input(
                "Monthly Spending Needs (USD)",
                min_value=1.0,
                value=DEFAULT_MONTHLY_SPENDING,
                help="Your estimated monthly expenses in retirement"
            )

            bitcoin_growth_rate_label = st.selectbox(
                "Bitcoin Growth Rate Projection",
                list(BITCOIN_GROWTH_RATE_OPTIONS.keys()),
                index=0
            )
            bitcoin_growth_rate = BITCOIN_GROWTH_RATE_OPTIONS[bitcoin_growth_rate_label]

            inflation_rate = st.number_input(
                "Inflation Rate (%)",
                min_value=0.0,
                value=DEFAULT_INFLATION_RATE,
                help="Expected annual inflation rate"
            )

            col6, col7 = st.columns(2)
            with col6:
                current_holdings = st.number_input(
                    "Current Bitcoin Holdings",
                    min_value=0.0,
                    max_value=HOLDINGS_MAX,
                    value=DEFAULT_CURRENT_HOLDINGS,
                    help="How much Bitcoin you currently own"
                )
            with col7:
                monthly_investment = st.number_input(
                    "Monthly Recurring Investment (USD)",
                    min_value=0.0,
                    value=DEFAULT_MONTHLY_INVESTMENT,
                    help="How much you invest in Bitcoin each month"
                )

            # Only show the submit button in the form
            submitted = st.form_submit_button("Calculate Retirement Plan")

    # Validate inputs
    if submitted:
        errors = validate_inputs(
            current_age, retirement_age, life_expectancy, monthly_spending,
            bitcoin_growth_rate, inflation_rate, current_holdings, monthly_investment
        )
        if errors:
            for err in errors:
                st.error(err)
            return

        # Show progress bar for calculations
        with st.spinner("Calculating your retirement plan..."):
            # Store current inputs in session state
            st.session_state.last_inputs = {
                'current_age': current_age,
                'retirement_age': retirement_age,
                'life_expectancy': life_expectancy,
                'monthly_spending': monthly_spending,
                'bitcoin_growth_rate': bitcoin_growth_rate,
                'inflation_rate': inflation_rate,
                'current_holdings': current_holdings,
                'monthly_investment': monthly_investment
            }

            # Get and cache the current Bitcoin price once
            current_bitcoin_price, price_warnings = cached_get_bitcoin_price()
            for warning_msg in price_warnings:
                st.warning(warning_msg)

            # Perform the calculation
            plan = calculate_bitcoin_needed(
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

            bitcoin_needed = plan.bitcoin_needed
            life_expectancy = plan.life_expectancy
            total_bitcoin_holdings = plan.total_bitcoin_holdings
            future_investment_value = plan.future_investment_value
            annual_expense_at_retirement = plan.annual_expense_at_retirement
            future_bitcoin_price = plan.future_bitcoin_price
            total_retirement_expenses = plan.total_retirement_expenses

        years_until_retirement = retirement_age - current_age
        retirement_duration = life_expectancy - retirement_age

        # Results section
        with st.expander("Retirement Summary", expanded=True):
            if total_bitcoin_holdings >= bitcoin_needed:
                result = (
                    f"✅ Great news! You will have enough Bitcoin to retire. "
                    f"You will retire at {retirement_age} and live comfortably until {life_expectancy} with {total_bitcoin_holdings:.4f} BTC. "
                    f"Your inflation-adjusted annual expenses at retirement will be ${annual_expense_at_retirement:,.2f}."
                )
            else:
                additional_bitcoin_needed = bitcoin_needed - total_bitcoin_holdings
                result = (
                    f"💡 You need an additional {additional_bitcoin_needed:.4f} Bitcoin to retire. "
                    f"You will retire at {retirement_age} and need {bitcoin_needed:.4f} BTC. "
                    f"Your inflation-adjusted annual expenses at retirement will be ${annual_expense_at_retirement:,.2f}."
                )

            st.success(result)

        with st.expander("Detailed Breakdown"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("Years Until Retirement:", f"{years_until_retirement} years")
                st.write("Current Bitcoin Price:", f"${current_bitcoin_price:,.2f}")
                st.write("Projected Price at Retirement:", f"${future_bitcoin_price:,.2f}")
                st.write("Bitcoin Needed at Retirement:", f"{bitcoin_needed:.4f} BTC")
            with col_b:
                st.write("Total Retirement Period:", f"{retirement_duration} years")
                st.write("Future Value of Investments:", f"${future_investment_value:,.2f}")
                st.write("Bitcoin from Investments:", f"{future_investment_value / future_bitcoin_price:.4f} BTC")
                st.write("Total Retirement Expenses:", f"${total_retirement_expenses:,.2f}")

        with st.expander("Verification"):
            st.write(f"With ${monthly_investment:,.2f}/month investment for {years_until_retirement} years at {bitcoin_growth_rate}% growth:")
            st.write(f"- Future value: ${future_investment_value:,.2f}")
            st.write(f"- Bitcoin from investments: {future_investment_value / future_bitcoin_price:.4f} BTC")
            st.write(f"At retirement:")
            st.write(f"- Annual expenses: ${annual_expense_at_retirement:,.2f}")
            st.write(f"- Total expenses over {retirement_duration} years: ${total_retirement_expenses:,.2f}")
            st.write(f"- Bitcoin needed: {bitcoin_needed:.4f} BTC")

        st.warning("Note: Bitcoin prices are highly volatile. These calculations are estimates and should not be considered financial advice.")

if __name__ == "__main__":
    main()
