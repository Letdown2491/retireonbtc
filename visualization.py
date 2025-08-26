# visualization.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections.abc import Sequence
import numpy as np

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

    df = pd.DataFrame({"Age": list(ages), "Holdings (₿)": list(holdings)})
    expenses_inputs = [
        monthly_spending,
        inflation_rate,
        current_bitcoin_price,
        bitcoin_growth_rate,
    ]
    if all(v is not None for v in expenses_inputs):
        price_series = current_bitcoin_price * (
            1 + bitcoin_growth_rate / 100
        ) ** np.arange(len(ages))
        expenses_usd = monthly_spending * 12 * (
            1 + inflation_rate / 100
        ) ** np.arange(len(ages))
        expenses_btc = expenses_usd / price_series
        df["Expenses (₿)"] = expenses_btc
        y = ["Holdings (₿)", "Expenses (₿)"]
    else:
        y = "Holdings (₿)"

    fig = px.line(df, x="Age", y=y)

    if isinstance(y, list):
        fig.data[0].line.color = "rgba(253, 150, 68, 1.0)"
        fig.data[0].fill = "tozeroy"
        fig.data[0].fillcolor = "rgba(253, 150, 68, 0.2)"
        for trace in fig.data[1:]:
            trace.fill = "tozeroy"
            trace.fillcolor = "rgba(99, 110, 250, 0.2)"
    else:
        fig.update_traces(
            line_color="rgba(253, 150, 68, 1.0)",
            fill="tozeroy",
            fillcolor="rgba(253, 150, 68, 0.2)",
        )
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )

def show_fan_chart(paths: Sequence | None, start_age: int) -> None:
    """Render a fan chart of simulated portfolio value in USD.

    Parameters
    ----------
    paths:
        Simulated USD value paths with shape ``(n_sims, years)``. ``None``
        disables rendering.
    start_age:
        Age corresponding to the first column of ``paths``.
    """

    if paths is None:
        return

    arr = np.asarray(paths, dtype=float)
    # Accept a single path of shape (years,) by upcasting to 2-D
    if arr.ndim == 1:
        arr = arr[np.newaxis, :]
    if arr.ndim != 2 or arr.shape[1] == 0:
        return

    ages = np.arange(start_age, start_age + arr.shape[1])
    percentiles = np.percentile(arr, [10, 25, 50, 75], axis=0)
    labels = ["p10", "p25", "p50", "p75"]
    df = pd.DataFrame({"Age": ages})
    for lab, series in zip(labels, percentiles):
        df[lab] = series

    fig = px.line(df, x="Age", y=labels)

    colors = {
        "p10": (255, 89, 94),
        "p25": (255, 202, 58),
        "p50": (138, 201, 38),
        "p75": (25, 130, 196),
    }
    for trace in fig.data:
        r, g, b = colors.get(trace.name, (0, 0, 0))
        trace.line.color = f"rgba({r}, {g}, {b}, 1)"
        trace.fill = "tozeroy"
        trace.fillcolor = f"rgba({r}, {g}, {b}, 0.2)"

    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0), showlegend=False, yaxis_title="Value (USD)"
    )
    st.plotly_chart(fig)


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
            "bitcoin_needed": "Bitcoin Needed (₿)",
            "total_bitcoin_holdings": "Total Bitcoin Holdings (₿)",
            "future_bitcoin_price": "Future Bitcoin Price (USD)",
        }
    )

    # Display the DataFrame
    st.dataframe(df)

    # Visualization
    fig = px.bar(
        df,
        x="Scenario",
        y=["Bitcoin Needed (₿)", "Total Bitcoin Holdings (₿)"],
        title="Bitcoin Needed vs. Projected Holdings",
        barmode="group",
        labels={"value": "Bitcoin (₿)", "variable": "Metric"},
    )
    st.plotly_chart(fig)
