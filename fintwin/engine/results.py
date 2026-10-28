"""Results generator: produces results.json from profile, plan, scenario.

Wires contract.py into actual results generation.
"""
from __future__ import annotations

import json
import sys, os

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from .core import diagnose, as_is_plan, Decision, risk_report

from .contract import ResultsJSON, Provenance, ProfileData, RiskData, PlanData, MCData
from data import Profile as TAProfile, Plan as TAPlan, Scenario as TAScenario, Tagged
from bridge import ta_profile_to_ft, ta_scenario_to_ft
from generate import generate_candidates, hard_filter
from rank import rank_plans
from montecarlo import monte_carlo


def _tagged_val(tagged):
    if isinstance(tagged, Tagged):
        return tagged.value
    return tagged


def generate_results(profile, decision_label, decision_amount, scenario, weights=None, n_mc=5000):
    """Generate the full results.json from tagged inputs."""
    ft_profile = ta_profile_to_ft(profile)
    ft_scenario = ta_scenario_to_ft(scenario)

    from .core import Decision, as_is_plan, diagnose
    ft_decision = Decision(label=decision_label, amount=decision_amount)
    dx = diagnose(ft_profile, ft_decision, ft_scenario)
    ft_risk = dx["adverse"]

    ranking = rank_plans(ft_profile, ft_decision, ft_scenario, weights=weights, n_mc=n_mc)
    mc_result = monte_carlo(ft_profile, as_is_plan(ft_decision), ft_scenario, n=n_mc)

    plans = []
    for p in ranking.get("all_feasible", []):
        plans.append(PlanData(
            id=p.get("id", ""),
            description=p.get("name", ""),
            feasible=True,
            reject_reason=None,
            min_cash_base=p.get("min_cash", 0),
            min_cash_stress=p.get("min_cash", 0),
            breach_prob=p.get("breach_prob"),
            ci=mc_result.get("ci"),
            delay_months=p.get("acquired_month", 0),
            extra_cost=p.get("cost", 0),
            label=p.get("pareto_label"),
        ))

    provenance = [
        Provenance(field="opening_cash", tag="ENTERED", source="user_input"),
        Provenance(field="reserve", tag="ENTERED", source="user_input"),
        Provenance(field="monthly_opex", tag="ENTERED", source="user_input"),
        Provenance(field="revenue_drop", tag="ENTERED", source="user_input"),
        Provenance(field="inflows", tag="UPLOAD", source="bank_statement.csv"),
    ]

    inflows = []
    for inf in profile.inflows.value:
        inflows.append({"amount": _tagged_val(inf.amount), "month": _tagged_val(inf.due_month), "status": _tagged_val(inf.status)})

    profile_data = ProfileData(
        cash=_tagged_val(profile.opening_cash),
        reserve=_tagged_val(profile.reserve),
        opex_by_month=[_tagged_val(profile.monthly_opex)] * _tagged_val(profile.horizon_months),
        loans=[{"monthly_payment": _tagged_val(l.monthly_payment), "start": _tagged_val(l.start_month), "end": _tagged_val(l.end_month)} for l in profile.loans.value],
        inflows=inflows,
    )

    risk_data = RiskData(
        first_breach_month=ft_risk.get("breach_month"),
        max_shortfall=ft_risk.get("shortfall", 0),
        kind="NONE" if ft_risk.get("passes") else ("TEMPORARY" if "revenue_shock" in ft_risk.get("single_fixes", []) else "PERSISTENT"),
        causes=[{"driver": k, "removal_clears_breach": k in ft_risk.get("single_fixes", [])} for k in ft_risk.get("causes", {})],
    )

    mc_data = MCData(
        enabled=mc_result.get("enabled", False),
        disabled_reason=mc_result.get("disabled_reason"),
        N=mc_result.get("N", 0),
        seed=mc_result.get("seed", 0),
        bands=mc_result.get("bands", {"p10": [], "p50": [], "p90": []}),
    )

    return ResultsJSON(
        provenance=provenance,
        profile=profile_data,
        series={},
        risk=risk_data,
        plans=plans,
        mc=mc_data,
    )


def results_to_json(results):
    """Serialize ResultsJSON to JSON string."""
    import dataclasses
    return json.dumps(dataclasses.asdict(results), indent=2, default=str)
