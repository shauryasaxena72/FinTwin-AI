"""Budget dashboard backend: aggregates cash, inflows, outflows, and plan metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BudgetSnapshot:
    opening_cash: float
    total_inflows: float
    total_outflows: float
    closing_cash: float
    reserve: float
    surplus: float
    deficit: float


def build_budget_dashboard(profile: Any, scenario: Any = None) -> dict:
    """Return a serialisable budget dashboard payload."""
    opening = profile.opening_cash.value
    reserve = profile.reserve.value
    inflows = profile.inflows.value
    loans = profile.loans.value
    total_inflows = sum(i.amount.value for i in inflows)
    loan_payments = sum(l.monthly_payment.value for l in loans)
    monthly_opex = profile.monthly_opex.value
    horizon = profile.horizon_months.value
    total_outflows = monthly_opex * horizon + loan_payments * horizon
    closing = opening + total_inflows - total_outflows
    surplus = closing - reserve
    deficit = max(0.0, reserve - closing)
    snap = BudgetSnapshot(
        opening_cash=opening,
        total_inflows=total_inflows,
        total_outflows=total_outflows,
        closing_cash=closing,
        reserve=reserve,
        surplus=surplus,
        deficit=deficit,
    )
    return {
        "snapshot": snap.__dict__,
        "inflow_count": len(inflows),
        "loan_count": len(loans),
        "horizon_months": horizon,
        "healthy": closing >= reserve,
    }


def affordability_check(profile: Any, amount: float, month: int) -> dict:
    """Static affordability check: can the profile afford `amount` at `month`?"""
    opening = profile.opening_cash.value
    reserve = profile.reserve.value
    inflows = profile.inflows.value
    loans = profile.loans.value
    monthly_opex = profile.monthly_opex.value
    inflow_to_date = sum(i.amount.value for i in inflows if i.due_month.value <= month)
    loan_paid = sum(l.monthly_payment.value for l in loans if l.start_month.value <= month <= l.end_month.value) * month
    opex_paid = monthly_opex * month
    cash_available = opening + inflow_to_date - opex_paid - loan_paid
    affordable = cash_available - amount >= reserve
    return {
        "affordable": affordable,
        "cash_available": cash_available,
        "amount": amount,
        "month": month,
        "reserve": reserve,
        "shortfall": max(0.0, amount + reserve - cash_available),
    }
