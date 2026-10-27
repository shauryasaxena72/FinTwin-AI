"""Bridge between FinTwin_AI (tagged model) and fintwin_prototype (engine model).

Converts between the two data models so both modules can work together.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fintwin_prototype", "fintwin"))

from fintwin.engine import Profile as FTProfile, Plan as FTPlan, Scenario as FTScenario, Decision as FTDecision, Receivable, Receivable
from FinTwin_AI.data import Profile as TAProfile, Plan as TAPlan, Scenario as TAScenario, Tagged, Inflow, Loan


def _tagged_val(tagged, default=None):
    """Extract raw value from a Tagged object or return as-is."""
    if isinstance(tagged, Tagged):
        return tagged.value
    return tagged


def ta_profile_to_ft(ta_profile: TAProfile) -> FTProfile:
    """Convert FinTwin_AI tagged Profile to fintwin.engine Profile."""
    # Extract monthly revenue from inflows
    monthly_revenue = 0.0
    for inflow in ta_profile.inflows.value:
        if inflow.category.value == "revenue":
            monthly_revenue += inflow.amount.value

    # Extract receivables
    receivables = []
    for inflow in ta_profile.inflows.value:
        if inflow.category.value == "revenue":
            receivables.append(Receivable(
                amount=inflow.amount.value,
                month=inflow.due_month.value,
                confirmed=(inflow.status.value == "confirmed"),
            ))

    # Extract monthly debt service from loans
    monthly_debt = 0.0
    for loan in ta_profile.loans.value:
        monthly_debt += loan.monthly_payment.value

    return FTProfile(
        opening_cash=_tagged_val(ta_profile.opening_cash),
        monthly_revenue=monthly_revenue,
        monthly_expenses=_tagged_val(ta_profile.monthly_opex),
        monthly_debt_service=monthly_debt,
        min_reserve=_tagged_val(ta_profile.reserve),
        collection_lag=0,
        horizon=_tagged_val(ta_profile.horizon_months),
        receivables=receivables,
    )


def ft_profile_to_ta(ft_profile: FTProfile, source: str = "fintwin_engine") -> TAProfile:
    """Convert fintwin.engine Profile to FinTwin_AI tagged Profile."""
    def tagged(value, tag="derived"):
        return Tagged(value=value, tag=tag, source=source)

    inflows = []
    for r in ft_profile.receivables:
        inflows.append(Inflow(
            amount=tagged(r.amount),
            due_month=tagged(r.month),
            status=tagged("confirmed" if r.confirmed else "expected"),
            category=tagged("revenue"),
            actual_pay_month=tagged(r.month if r.confirmed else None),
            expected_pay_month=tagged(r.month if not r.confirmed else None),
            customer=tagged("receivable"),
        ))

    loans = []
    if ft_profile.monthly_debt_service > 0:
        loans.append(Loan(
            monthly_payment=tagged(ft_profile.monthly_debt_service),
            start_month=tagged(1),
            end_month=tagged(ft_profile.horizon),
            label=tagged("debt service"),
        ))

    return TAProfile(
        opening_cash=tagged(ft_profile.opening_cash),
        reserve=tagged(ft_profile.min_reserve),
        monthly_opex=tagged(ft_profile.monthly_expenses),
        horizon_months=tagged(ft_profile.horizon),
        inflows=tagged(tuple(inflows)),
        loans=tagged(tuple(loans)),
    )


def ta_scenario_to_ft(ta_scenario: TAScenario) -> FTScenario:
    """Convert FinTwin_AI tagged Scenario to fintwin.engine Scenario."""
    return FTScenario(
        name=_tagged_val(ta_scenario.name),
        revenue_shock_pct=-_tagged_val(ta_scenario.revenue_drop_fraction),
        shock_start=_tagged_val(ta_scenario.revenue_drop_start_month),
        one_off_shock=_tagged_val(ta_scenario.one_off_shock_amount),
        one_off_month=_tagged_val(ta_scenario.one_off_shock_month),
    )


def ft_scenario_to_ta(ft_scenario: FTScenario, source: str = "fintwin_engine") -> TAScenario:
    """Convert fintwin.engine Scenario to FinTwin_AI tagged Scenario."""
    def tagged(value, tag="derived"):
        return Tagged(value=value, tag=tag, source=source)

    return TAScenario(
        name=tagged(ft_scenario.name),
        revenue_drop_fraction=tagged(-ft_scenario.revenue_shock_pct),
        revenue_drop_start_month=tagged(ft_scenario.shock_start),
        payment_delay_months=tagged(0),
        one_off_shock_amount=tagged(ft_scenario.one_off_shock),
        one_off_shock_month=tagged(ft_scenario.one_off_month),
    )


def ta_plan_to_ft(ta_plan: TAPlan, plan_id: str = "ta_plan") -> FTPlan:
    """Convert FinTwin_AI tagged Plan to fintwin.engine Plan."""
    purchase_month = _tagged_val(ta_plan.purchase_month)
    purchase_amount = _tagged_val(ta_plan.purchase_amount)
    return FTPlan(
        id=plan_id,
        name=_tagged_val(ta_plan.name),
        kind="as_is",
        purchase={purchase_month: purchase_amount} if purchase_amount > 0 else {},
        expense_cut_pct=_tagged_val(ta_plan.monthly_opex_reduction),
        cut_months=_tagged_val(ta_plan.reduction_end_month) - _tagged_val(ta_plan.reduction_start_month) + 1
                   if _tagged_val(ta_plan.reduction_end_month) > 0 else 0,
        extra_cost=0.0,
        goal_curve=[1.0],
        acquired_month=0,
        notes="",
    )


def ft_plan_to_ta(ft_plan: FTPlan, source: str = "fintwin_engine") -> TAPlan:
    """Convert fintwin.engine Plan to FinTwin_AI tagged Plan."""
    def tagged(value, tag="derived"):
        return Tagged(value=value, tag=tag, source=source)

    purchase_month = 0
    purchase_amount = 0.0
    if ft_plan.purchase:
        purchase_month = min(ft_plan.purchase.keys())
        purchase_amount = sum(ft_plan.purchase.values())

    return TAPlan(
        name=tagged(ft_plan.name),
        purchase_amount=tagged(purchase_amount),
        purchase_month=tagged(purchase_month),
        monthly_opex_reduction=tagged(ft_plan.expense_cut_pct),
        reduction_start_month=tagged(1),
        reduction_end_month=tagged(ft_plan.cut_months),
    )
