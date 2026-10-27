"""Cash reserve breach detection and counterfactual attribution."""

from __future__ import annotations

from dataclasses import replace

from FinTwin_AI.cashflow import forecast
from FinTwin_AI.data import Plan, Profile, Scenario


def assess_risk(
    profile: Profile,
    plan: Plan,
    scenario: Scenario,
    *,
    strict: bool = True,
) -> dict[str, object]:
    months = forecast(profile, plan, scenario, strict=strict)
    reserve = profile.reserve.value
    breached = [result.month for result in months if result.closing_cash < reserve]
    minimum_cash = min(
        [profile.opening_cash.value, *(result.closing_cash for result in months)]
    )
    first_breach = breached[0] if breached else None
    recovered = bool(
        breached
        and any(
            result.month > first_breach and result.closing_cash >= reserve
            for result in months
        )
    )
    report: dict[str, object] = {
        "passes": not breached,
        "first_breach_month": first_breach,
        "max_shortfall": round(max(0.0, reserve - minimum_cash), 2),
        "minimum_cash": round(minimum_cash, 2),
        "breach_type": (
            "NONE" if not breached else "TEMPORARY" if recovered else "PERSISTENT"
        ),
        "runway_month": next(
            (result.month for result in months if result.closing_cash < 0),
            None,
        ),
        "months": months,
        "clearing_counterfactuals": [],
    }

    if breached:
        counterfactuals: list[tuple[str, Plan, Scenario]] = [
            (
                "purchase",
                replace(plan, purchase_amount=replace(plan.purchase_amount, value=0.0)),
                scenario,
            ),
            (
                "revenue_drop",
                plan,
                replace(
                    scenario,
                    revenue_drop_fraction=replace(
                        scenario.revenue_drop_fraction, value=0.0
                    ),
                ),
            ),
            (
                "payment_delay",
                plan,
                replace(
                    scenario,
                    payment_delay_months=replace(
                        scenario.payment_delay_months, value=0
                    ),
                ),
            ),
            (
                "one_off_shock",
                plan,
                replace(
                    scenario,
                    one_off_shock_amount=replace(
                        scenario.one_off_shock_amount, value=0.0
                    ),
                ),
            ),
        ]
        clears: list[str] = []
        for name, counterfactual_plan, counterfactual_scenario in counterfactuals:
            counterfactual = forecast(
                profile, counterfactual_plan, counterfactual_scenario, strict=strict
            )
            if all(item.closing_cash >= reserve for item in counterfactual):
                clears.append(name)
        report["clearing_counterfactuals"] = clears
    return report
