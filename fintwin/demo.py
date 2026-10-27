"""CLI demo / demo-day fallback: python demo.py

Shows three scenarios: green (healthy), red (stressed), and mixed (borderline).
"""
from fintwin.engine import Profile, Decision, Scenario
from fintwin.copilot import FinTwinAgent

SCENARIOS = {
    "GREEN (Healthy)": {
        "profile": Profile(opening_cash=20, monthly_revenue=8, monthly_expenses=5, min_reserve=3, horizon=12),
        "decision": Decision("Buy equipment", 4.0),
        "scenario": Scenario("adverse", -0.20, 1, 1.5, 3),
    },
    "RED (Stressed)": {
        "profile": Profile(opening_cash=5, monthly_revenue=3, monthly_expenses=4, min_reserve=3, horizon=12),
        "decision": Decision("Buy equipment", 4.0),
        "scenario": Scenario("adverse", -0.20, 1, 1.5, 3),
    },
    "MIXED (Borderline)": {
        "profile": Profile(opening_cash=10, monthly_revenue=5, monthly_expenses=4.5, min_reserve=3, horizon=12),
        "decision": Decision("Buy equipment", 4.0),
        "scenario": Scenario("adverse", -0.20, 1, 1.5, 3),
    },
}

for name, data in SCENARIOS.items():
    print(f"\n{'='*60}")
    print(f"  SCENARIO: {name}")
    print(f"{'='*60}")
    a = FinTwinAgent()
    a.profile = data["profile"]
    a.decision = data["decision"]
    a.scenario = data["scenario"]
    for q in ("Can I afford this?", "What are the best alternatives?", "Why does it fail?"):
        print(f"\n> {q}\n{a.chat(q)}")
    print()
"