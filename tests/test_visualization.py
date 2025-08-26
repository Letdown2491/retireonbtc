import importlib
import types
import numpy as np

viz = importlib.import_module("visualization")
calc = importlib.import_module("calculations")

def test_compare_scenarios_smoke():
    compare = getattr(viz, "compare_scenarios", None)
    assert isinstance(compare, types.FunctionType), "visualization.compare_scenarios not found"

    scenarios = [
        {"label": "Base", "btc_needed": 5.0, "projected_btc": 3.0},
        {"label": "Aggressive", "btc_needed": 4.0, "projected_btc": 3.5},
    ]
    # Expect it to render without exploding; many viz functions return (fig, df) or None
    out = compare(scenarios)
    assert out is None or isinstance(out, tuple) or isinstance(out, dict)

def test_progress_visualization_smoke():
    series = calc.project_holdings_over_time(
        current_age=35, retirement_age=65, life_expectancy=85,
        bitcoin_growth_rate=0.05, inflation_rate=0.02,
        current_holdings=0.1, monthly_investment=200.0,
        monthly_spending=1200.0, current_bitcoin_price=50_000.0
    )
    show = getattr(viz, "show_progress_visualization", None)
    if isinstance(show, types.FunctionType):
        assert show(series) is None  # Precomputed holdings
        assert (
            show(
                None,
                current_age=35,
                retirement_age=65,
                life_expectancy=85,
                bitcoin_growth_rate=0.05,
                inflation_rate=0.02,
                current_holdings=0.1,
                monthly_investment=200.0,
                monthly_spending=1200.0,
                current_bitcoin_price=50_000.0,
            )
            is None
        )


def test_fan_chart_smoke(monkeypatch):
    captured = []
    fake_st = types.SimpleNamespace(plotly_chart=lambda fig, *a, **k: captured.append(fig))
    monkeypatch.setattr(viz, "st", fake_st)

    paths = np.zeros((5, 3))
    assert viz.show_fan_chart(paths, 30) is None

    fig = captured.pop()
    expected = {
        "p10": ("rgba(255, 89, 94, 1)", "rgba(255, 89, 94, 0.2)"),
        "p25": ("rgba(255, 202, 58, 1)", "rgba(255, 202, 58, 0.2)"),
        "p50": ("rgba(138, 201, 38, 1)", "rgba(138, 201, 38, 0.2)"),
        "p75": ("rgba(25, 130, 196, 1)", "rgba(25, 130, 196, 0.2)"),
        "p90": ("rgba(106, 76, 147, 1)", "rgba(106, 76, 147, 0.2)"),
    }
    for trace in fig.data:
        line_color, fill_color = expected[trace.name]
        assert trace.line.color == line_color
        assert trace.fill == "tozeroy"
        assert trace.fillcolor == fill_color

    # Single path should also be handled gracefully
    assert viz.show_fan_chart(np.zeros(3), 30) is None
