# visualization.py
import streamlit as st
import pandas as pd
import plotly.express as px

from calculations import project_holdings_over_time

def show_progress_visualization(
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
    """Visualize projected Bitcoin holdings over time.

    The projection mirrors the calculations in ``calculate_bitcoin_needed`` by
    accounting for investment growth before retirement and withdrawals to cover
    expenses after retirement.

    Args:
        current_age: User's current age.
        retirement_age: Age at which the user plans to retire.
        life_expectancy: Expected lifespan.
        bitcoin_growth_rate: Expected annual growth rate of Bitcoin (percentage).
        inflation_rate: Expected annual inflation rate (percentage).
        current_holdings: Current Bitcoin holdings in BTC.
        monthly_investment: Recurring monthly investment in USD.
        monthly_spending: Monthly spending needs in USD at today's value.
        current_bitcoin_price: Current price of Bitcoin in USD.
    """

    ages = list(range(current_age, life_expectancy + 1))
    holdings = project_holdings_over_time(
        current_age,
        retirement_age,
        life_expectancy,
        bitcoin_growth_rate,
        inflation_rate,
        current_holdings,
        monthly_investment,
        monthly_spending,
        current_bitcoin_price,
    )

    df = pd.DataFrame({"Age": ages, "BTC Holdings": holdings})
    fig = px.line(df, x="Age", y="BTC Holdings")
    st.plotly_chart(fig, use_container_width=True)

def compare_scenarios(scenarios):
    st.subheader("Scenario Comparison")
    st.markdown("Compare different retirement plans side-by-side.")

    # Create a DataFrame from the scenarios list
    df = pd.DataFrame(scenarios)

    # Add a scenario label column for user-friendly display
    df.insert(0, "Scenario", [f"Scenario {i + 1}" for i in range(len(df))])

    # Rename columns to user-facing labels
    df = df.rename(
        columns={
            "current_age": "Current Age",
            "retirement_age": "Retirement Age",
            "life_expectancy": "Life Expectancy",
            "bitcoin_needed": "Bitcoin Needed (BTC)",
            "total_bitcoin_holdings": "Total Bitcoin Holdings (BTC)",
            "future_bitcoin_price": "Future Bitcoin Price (USD)",
        }
    )

    # Display the DataFrame
    st.dataframe(df)

    # Visualization
    fig = px.bar(
        df,
        x="Scenario",
        y=["Bitcoin Needed (BTC)", "Total Bitcoin Holdings (BTC)"],
        title="Bitcoin Needed vs. Projected Holdings",
        barmode="group",
        labels={"value": "Bitcoin (BTC)", "variable": "Metric"},
    )
    st.plotly_chart(fig)
