# visualization.py
import streamlit as st
import pandas as pd
import plotly.express as px
from collections.abc import Sequence

from calculations import project_holdings_over_time


def show_progress_visualization(
    holdings: Sequence | None,
    current_age: int | None = None,
    retirement_age: int | None = None,
    life_expectancy: int | None = None,
    bitcoin_growth_rate: float | None = None,
    inflation_rate: float | None = None,
    current_holdings: float | None = None,
    monthly_investment: float | None = None,
    monthly_spending: float | None = None,
    current_bitcoin_price: float | None = None,
) -> None:
    """Visualize projected Bitcoin holdings over time.

    The first argument is a holdings sequence representing BTC holdings by age.
    If ``holdings`` is ``None`` the sequence will be derived from the supplied
    parameters via :func:`project_holdings_over_time`. When only a holdings
    series is provided the ages are inferred from the series itself.
    """

    if holdings is None:
        required = [
            current_age,
            retirement_age,
            life_expectancy,
            bitcoin_growth_rate,
            inflation_rate,
            current_holdings,
            monthly_investment,
            monthly_spending,
            current_bitcoin_price,
        ]
        if any(v is None for v in required):
            raise ValueError("Missing parameters for holdings projection")

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
    else:
        if isinstance(holdings, pd.Series):
            ages = holdings.index
            holdings = holdings.values
        else:
            holdings = list(holdings)
            if current_age is not None:
                ages = range(current_age, current_age + len(holdings))
            else:
                ages = range(len(holdings))

    df = pd.DataFrame({"Age": list(ages), "BTC Holdings": list(holdings)})
    fig = px.line(df, x="Age", y="BTC Holdings")
    st.plotly_chart(fig, use_container_width=True)

def compare_scenarios(scenarios: list[dict]) -> None:
    """Display a side-by-side comparison of retirement scenarios.

    Args:
        scenarios: Sequence of scenario mappings. Each scenario must contain
            the following keys:

            - ``current_age``: Current age of the user.
            - ``retirement_age``: Planned retirement age.
            - ``life_expectancy``: Expected lifespan.
            - ``bitcoin_needed``: Bitcoin required at retirement.
            - ``total_bitcoin_holdings``: Projected Bitcoin holdings at
              retirement.
            - ``future_bitcoin_price``: Estimated Bitcoin price at retirement
              (in USD).

    Returns:
        None
    """

    st.subheader("Scenario Comparison")
    st.markdown("Compare different retirement plans side-by-side.")

    compare_clicked = st.button("Compare Scenarios", disabled=not scenarios)

    if not scenarios:
        st.info("No scenarios to compare.")
        return

    if not compare_clicked:
        return

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
