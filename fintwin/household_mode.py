"""Household/personal mode: simpler profile for personal finance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HouseholdProfile:
    monthly_income: float
    monthly_expenses: float
    savings: float
    debt_payments: float
    horizon_months: int

def to_profile(hp: HouseholdProfile) -> Any:
    """Convert HouseholdProfile to standard Profile-compatible dict."""
    return {
        "opening_cash": hp.savings,
        "monthly_revenue": hp.monthly_income,
        "monthly_expenses": hp.monthly_expenses,
        "monthly_debt_service": hp.debt_payments,
        "horizon": hp.horizon_months,
    }
