"""Unified tagged data model for FinTwin AI backend.

Consolidates Tagged inputs, dataclasses, validation, and CSV ingestion.
Every field carries a Tagged(value, tag, source) for provenance tracking.
"""
from __future__ import annotations

# Tagged data model (from data.py)
from data import (
    Tagged,
    Inflow,
    Loan,
    Plan,
    Scenario,
    Profile,
    ClassifiedRow,
    InflowStatus,
    RowCategory,
    validate_profile,
    validate_month_coverage,
    suggest_category,
    parse_csv_rows,
)

# Bridge conversions
from bridge import (
    ta_profile_to_ft,
    ft_profile_to_ta,
    ta_scenario_to_ft,
    ft_scenario_to_ta,
    ta_plan_to_ft,
    ft_plan_to_ta,
)

__all__ = [
    "Tagged", "Inflow", "Loan", "Plan", "Scenario", "Profile", "ClassifiedRow",
    "InflowStatus", "RowCategory", "validate_profile", "validate_month_coverage",
    "suggest_category", "parse_csv_rows",
    "ta_profile_to_ft", "ft_profile_to_ta", "ta_scenario_to_ft",
    "ft_scenario_to_ta", "ta_plan_to_ft", "ft_plan_to_ta",
]
