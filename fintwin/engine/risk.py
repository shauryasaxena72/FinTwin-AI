"""Unified risk detection for FinTwin AI backend.

Combines FinTwin_AI risk assessment (TEMPORARY/PERSISTENT, counterfactuals)
with fintwin risk_report (causes, single_fixes).
"""
from __future__ import annotations
import sys, os

_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from .core import risk_report
from risk import assess_risk as ta_assess_risk

from bridge import ta_profile_to_ft, ta_scenario_to_ft, ta_plan_to_ft


def assess_risk_tagged(profile, plan, scenario, *, strict=True):
    """Assess risk using FinTwin_AI tagged model."""
    return ta_assess_risk(profile, plan, scenario, strict=strict)


def assess_risk_engine(profile, plan, scenario):
    """Assess risk using fintwin engine model."""
    return risk_report(profile, plan, scenario)


def unified_risk(profile_ta, plan_ta, scenario_ta):
    """Run both risk assessments and return combined result."""
    ft_profile = ta_profile_to_ft(profile_ta)
    ft_scenario = ta_scenario_to_ft(scenario_ta)
    ft_plan = ta_plan_to_ft(plan_ta)

    ta_report = ta_assess_risk(profile_ta, plan_ta, scenario_ta, strict=True)
    ft_report = risk_report(ft_profile, ft_plan, ft_scenario)

    return {
        "tagged": ta_report,
        "engine": ft_report,
        "first_breach_month": ta_report.get("first_breach_month"),
        "max_shortfall": ta_report.get("max_shortfall"),
        "breach_type": ta_report.get("breach_type"),
        "runway_month": ta_report.get("runway_month"),
        "clearing_counterfactuals": ta_report.get("clearing_counterfactuals", []),
        "causes": ft_report.get("causes", {}),
        "single_fixes": ft_report.get("single_fixes", []),
        "passes": ta_report.get("passes", False),
        "min_cash": ft_report.get("min_cash"),
        "min_month": ft_report.get("min_month"),
    }
