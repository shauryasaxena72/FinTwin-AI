import numpy as np
from engine.core import *
from planner import rank_plans, generate_candidates
from montecarlo import monte_carlo
from copilot import FinTwinAgent

P, D, S = Profile(), Decision(), Scenario()

def test_base_path_matches_deck():           # 8-4=4, +1/month
    assert risk_report(P, as_is_plan(D), BASE)["cash"][:7] == [4, 5, 6, 7, 8, 9, 10]

def test_adverse_path_matches_deck():        # revenue -20% => surplus 0; -1.5 at M3
    r = risk_report(P, as_is_plan(D), S)
    assert r["cash"][:7] == [4, 4, 4, 2.5, 2.5, 2.5, 2.5]
    assert r["breach_month"] == 3 and r["shortfall"] == 0.5 and not r["passes"]

def test_looks_safe_then_fails_and_causes():
    dx = diagnose(P, D, S)
    assert dx["looks_safe_then_fails"]
    assert dx["adverse"]["causes"] == {"purchase_paid": 4.0, "revenue_loss": 3.0, "one_off_shock": 1.5}
    assert set(dx["adverse"]["single_fixes"]) == {"purchase", "revenue_shock", "one_off_shock"}

def test_collection_lag_shifts_receipts():
    p = Profile(collection_lag=2)
    c = collections(p, S)
    assert c[1] == 5 and c[2] == 5 and c[3] == 4          # shock billed M1 arrives M3

def test_confirmed_vs_expected_funds():
    p = Profile(receivables=[Receivable(2.0, 2, True), Receivable(3.0, 2, False)])
    assert forecast(p, as_is_plan(D), BASE).cash[2] == 6 + 2     # only confirmed counted

def test_all_ranked_plans_are_feasible_and_sorted():
    r = rank_plans(P, D, S, n_mc=300)
    assert r["n_feasible"] > 0 and len(r["ranked"]) == 3
    sc = [x["score"] for x in r["ranked"]]; assert sc == sorted(sc)
    assert all(x["min_cash"] >= P.min_reserve for x in r["all_feasible"])
    assert "as_is" not in [x["id"] for x in r["all_feasible"]]

def test_installment_interest_hand_calc():
    c = {p.id: p for p in generate_candidates(P, D)}["inst50x3"]
    # balance 2.0, principal 2/3 per month, 1% monthly: 0.02 + 0.01333 + 0.00667 = 0.04
    assert abs(c.extra_cost - 0.04) < 1e-3 and abs(sum(c.purchase.values()) - 4.04) < 1e-3

def test_monte_carlo_deterministic_and_ordered():
    best = rank_plans(P, D, S, n_mc=300)["ranked"][0]
    assert monte_carlo(P, as_is_plan(D), S, 500)["breach_prob"] == monte_carlo(P, as_is_plan(D), S, 500)["breach_prob"]
    assert monte_carlo(P, as_is_plan(D), S, 500)["breach_prob"] > best["breach_prob"]

def test_grounding_guard_flags_invented_numbers():
    a = FinTwinAgent(); a.call_tool("diagnose_decision", {})
    outs = [t["output"] for t in a.tool_log]
    assert a.ungrounded("Cash hits 2.5 in month 3, 0.5 short", outs) == []
    assert a.ungrounded("You will lose 47.3 lakh", outs) == ["47.3"]

def test_agent_offline_answers():
    a = FinTwinAgent()
    assert "fails under stress" in a.chat("Can I afford this?")
    assert "survive" in a.chat("best alternatives?")
    assert "month 3" in a.chat("why does it fail") 
    out = a.chat("what if cash 10 and revenue drops 30%")
    assert "revenue_shock_pct" in out and "opening_cash" in out
