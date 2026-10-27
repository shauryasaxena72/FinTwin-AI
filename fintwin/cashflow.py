"""Deterministic monthly cash-flow projection."""

from __future__ import annotations

from dataclasses import dataclass

from data import Plan, Profile, Scenario, validate_profile


@dataclass(frozen=True)
class MonthResult:
    month: int
    opening_cash: float
    confirmed_receipts: float
    expected_receipts: float
    operating_expenses: float
    loan_payments: float
    purchase_outflow: float
    one_off_shock: float
    closing_cash: float


def forecast(
    profile: Profile,
    plan: Plan,
    scenario: Scenario,
    *,
    strict: bool = True,
) -> list[MonthResult]:
    """Forecast each month; strict mode excludes expected receipts."""
    validate_profile(profile)
    horizon = profile.horizon_months.value
    if plan.purchase_amount.value < 0:
        raise ValueError("Purchase amount cannot be negative.")
    if plan.purchase_month.value < 1:
        raise ValueError("Purchase month must be month 1 or later.")
    if plan.monthly_opex_reduction.value < 0:
        raise ValueError("Operating expense reduction cannot be negative.")
    if plan.reduction_start_month.value < 1 or plan.reduction_end_month.value < 0:
        raise ValueError("Operating expense reduction months must be valid.")
    if plan.reduction_end_month.value not in (0,) and (
        plan.reduction_end_month.value < plan.reduction_start_month.value
    ):
        raise ValueError("Operating expense reduction end month must not precede its start.")
    if not 0 <= scenario.revenue_drop_fraction.value <= 1:
        raise ValueError("Revenue drop must be between 0 and 1.")
    if scenario.revenue_drop_start_month.value < 1:
        raise ValueError("Revenue drop start month must be month 1 or later.")
    if scenario.payment_delay_months.value < 0:
        raise ValueError("Payment delay cannot be negative.")
    if scenario.one_off_shock_amount.value < 0:
        raise ValueError("One-off shock amount cannot be negative.")
    if scenario.one_off_shock_month.value < 1:
        raise ValueError("One-off shock month must be month 1 or later.")
    cash = profile.opening_cash.value
    results: list[MonthResult] = []

    for month in range(1, horizon + 1):
        confirmed = 0.0
        expected = 0.0
        for inflow in profile.inflows.value:
            scheduled_month = (
                inflow.actual_pay_month.value
                if inflow.status.value == "confirmed"
                else inflow.expected_pay_month.value
            )
            receipt_month = scheduled_month + scenario.payment_delay_months.value
            if receipt_month != month:
                continue
            amount = inflow.amount.value
            if (
                inflow.category.value == "revenue"
                and month >= scenario.revenue_drop_start_month.value
            ):
                amount *= 1 - scenario.revenue_drop_fraction.value
            if inflow.status.value == "confirmed":
                confirmed += amount
            else:
                expected += amount

        reduction = 0.0
        if plan.reduction_start_month.value <= month <= plan.reduction_end_month.value:
            reduction = plan.monthly_opex_reduction.value
        operating_expenses = max(0.0, profile.monthly_opex.value - reduction)
        loan_payments = sum(
            loan.monthly_payment.value
            for loan in profile.loans.value
            if loan.start_month.value <= month <= loan.end_month.value
        )
        purchase = (
            plan.purchase_amount.value
            if plan.purchase_month.value == month
            else 0.0
        )
        shock = (
            scenario.one_off_shock_amount.value
            if scenario.one_off_shock_month.value == month
            else 0.0
        )
        receipts = confirmed + (0.0 if strict else expected)
        closing = cash + receipts - operating_expenses - loan_payments - purchase - shock
        results.append(
            MonthResult(
                month=month,
                opening_cash=round(cash, 2),
                confirmed_receipts=round(confirmed, 2),
                expected_receipts=round(expected, 2),
                operating_expenses=round(operating_expenses, 2),
                loan_payments=round(loan_payments, 2),
                purchase_outflow=round(purchase, 2),
                one_off_shock=round(shock, 2),
                closing_cash=round(closing, 2),
            )
        )
        cash = closing
    return results
