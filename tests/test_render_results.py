import importlib
from calculations import RetirementPlan, compute_health_score_basic

main = importlib.import_module("main")

class DummyCtx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass


class DummyStreamlit:
    def expander(self, *args, **kwargs):
        return DummyCtx()
    def columns(self, n):
        return [DummyCtx() for _ in range(n)]
    def write(self, *args, **kwargs):
        pass
    def success(self, *args, **kwargs):
        pass
    def warning(self, *args, **kwargs):
        pass
    def metric(self, *args, **kwargs):
        pass
    def info(self, *args, **kwargs):
        pass


def test_render_results_returns_health_score(monkeypatch):
    monkeypatch.setattr(main, "st", DummyStreamlit())
    monkeypatch.setattr(main, "show_progress_visualization", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "project_holdings_over_time", lambda **kwargs: [3, 2, 1, 0])

    plan = RetirementPlan(
        bitcoin_needed=2.0,
        life_expectancy=33,
        total_bitcoin_holdings=3.0,
        future_investment_value=0.0,
        annual_expense_at_retirement=0.0,
        future_bitcoin_price=1.0,
        total_retirement_expenses=0.0,
    )
    inputs = {
        "current_age": 30,
        "retirement_age": 31,
        "life_expectancy": 33,
        "bitcoin_growth_rate": 0.0,
        "inflation_rate": 0.0,
        "current_holdings": 0.0,
        "monthly_investment": 0.0,
        "monthly_spending": 0.0,
    }
    score, details = main.render_results(plan, inputs, 1.0, None)
    assert score == compute_health_score_basic(1.5, 2)
    assert details["funding_ratio"] == 1.5
