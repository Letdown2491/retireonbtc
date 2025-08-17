# visualization.py
import streamlit as st
import pandas as pd
import plotly.express as px

def show_progress_visualization(current_age, retirement_age, life_expectancy):
    # ... (rest of your function)
    pass # This is just a placeholder, replace with your actual code

def compare_scenarios(scenarios):
    st.subheader("Scenario Comparison")
    st.markdown("Compare different retirement plans side-by-side.")

    # Create a DataFrame from the scenarios list
    df = pd.DataFrame({
        "Scenario": [f"Scenario {i+1}" for i, s in enumerate(scenarios)],
        "Current Age": [s["current_age"] for s in scenarios],
        "Retirement Age": [s["retirement_age"] for s in scenarios],
        # Correct the syntax here
        "Life Expectancy": [s["life_expectancy"] for s in scenarios],
        "Bitcoin Needed (BTC)": [s["bitcoin_needed"] for s in scenarios],
        "Total Bitcoin Holdings (BTC)": [s["total_bitcoin_holdings"] for s in scenarios],
        "Future Bitcoin Price (USD)": [s["future_bitcoin_price"] for s in scenarios],
    })

    # Display the DataFrame
    st.dataframe(df)

    # Visualization
    fig = px.bar(
        df,
        x="Scenario",
        y=["Bitcoin Needed (BTC)", "Total Bitcoin Holdings (BTC)"],
        title="Bitcoin Needed vs. Projected Holdings",
        barmode="group",
        labels={"value": "Bitcoin (BTC)", "variable": "Metric"}
    )
    st.plotly_chart(fig)
