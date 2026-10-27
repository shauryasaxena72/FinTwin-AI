"""Candidate plan generator with hard filters and machine-readable reject_reason."""
from __future__ import annotations
import numpy as np
from .engine import Profile, Decision, Scenario, Plan, as_is_plan, risk_report

CUT_PAIN = 0.5
LOAN_RATE = 0.12

# Machine-readable reject reasons
REJECT_BASE_BREACH = "base_closing_below_reserve"
REJECT_GOAL_MISSED = "goal_not_achieved_by_deadline"
REJECT_LOAN_UNPAID = "loan_or_payroll_unpaid"


def _curve(H, pay, P):
    cum = np.cumsum([pay.get(m, 0.0) for m in range(H + 1)]) / P
    return [round(float(x), 3) for x in np.minimum(cum, 1.0)]


def _structures(profile: Profile, d: Decision) -> list:
    H, P, out = profile.horizon, d.amount, []
    out.append(as_is_plan(d))
    out[-1].goal_curve = [1.0] * (H + 1)
    for k in range(1, 7):
        out.append(Plan(f"delay{k}", f"Delay {d.label.lower()} {k} mo", "delay", {k: P},
                        goal_curve=[0.0] * k + [1.0] * (H + 1 - k), acquired_month=k))
    for n in (2, 3, 4):
        for s in (1, 2, 3):
            pay = {i * s: P / n for i in range(n)}
            if max(pay) <= H:
                out.append(Plan(f"phase{n}x{s}", f"Phase in {n} tranches every {s} mo", "phase", pay,
                                goal_curve=_curve(H, pay, P), acquired_month=max(pay)))
    for down in (0.3, 0.4, 0.5):
        for n in (3, 6, 9):
            bal, r, pay, interest = P * (1 - down), LOAN_RATE / 12, {0: P * down}, 0.0
            for m in range(1, n + 1):
                i = bal * r; interest += i; pay[m] = (P * (1 - down)) / n + i; bal -= (P * (1 - down)) / n
            out.append(Plan(f"inst{int(down*100)}x{n}", f"{int(down*100)}% down + {n} installments",
                            "installments", pay, extra_cost=round(interest, 3), goal_curve=[1.0] * (H + 1),
                            notes=f"{LOAN_RATE:.0%} p.a. financing"))
    for lag in (2, 3):
        out.append(Plan(f"credit{lag}", f"Negotiate: 50% now, 50% after {lag} mo (+2% price)", "negotiate",
                        {0: P * 0.5, lag: P * 0.5 + P * 0.02}, extra_cost=round(P * 0.02, 3),
                        goal_curve=[1.0] * (H + 1), notes="Assumes supplier accepts"))
    return out


def generate_candidates(profile: Profile, d: Decision, real_inputs: dict | None = None) -> list:
    """Generate candidate plans. A plan type exists only if its real input was provided."""
    real_inputs = real_inputs or {}
    cands = []
    for s in _structures(profile, d):
        cands.append(s)
        if s.kind == "as_is":
            continue
        for pct, months in ((0.10, 3), (0.10, 6), (0.15, 3), (0.15, 6)):
            savings = profile.monthly_expenses * pct * months
            cands.append(Plan(f"{s.id}+cut{int(pct*100)}x{months}",
                              f"{s.name} + cut costs {int(pct*100)}% for {months} mo",
                              "hybrid", dict(s.purchase), pct, months,
                              round(s.extra_cost + CUT_PAIN * savings, 3),
                              s.goal_curve, s.acquired_month, s.notes))
    return cands


def hard_filter(profile: Profile, plan: Plan, sc: Scenario) -> tuple[bool, str | None]:
    """Return (feasible, reject_reason). Machine-readable reject reasons."""
    rep = risk_report(profile, plan, sc)
    if not rep["passes"]:
        return False, REJECT_BASE_BREACH
    if plan.goal_curve and len(plan.goal_curve) > 0:
        if plan.goal_curve[-1] < 1.0 - 1e-9:
            return False, REJECT_GOAL_MISSED
    f_cash = rep.get("cash", [])
    if any(c < -1e-9 for c in f_cash):
        return False, REJECT_LOAN_UNPAID
    return True, None


def filter_candidates(profile: Profile, plans: list, sc: Scenario) -> tuple[list, list]:
    """Split plans into (feasible, rejected) with reject_reason attached."""
    feasible, rejected = [], []
    for p in plans:
        ok, reason = hard_filter(profile, p, sc)
        if ok:
            feasible.append(p)
        else:
            rejected.append((p, reason))
    return feasible, rejected
