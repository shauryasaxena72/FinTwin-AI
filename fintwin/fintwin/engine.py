"""Deterministic digital-twin engine. Every number the copilot may quote comes from here.
Units: Rs lakh. Month 0 = decision month; revenue/expense flows start at month 1."""
from __future__ import annotations
from dataclasses import dataclass, field, replace
import numpy as np


@dataclass
class Receivable:
    amount: float
    month: int
    confirmed: bool = True      # confirmed funds count in the deterministic twin
    p_pay: float = 0.8          # expected (unconfirmed) funds only enter Monte Carlo


@dataclass
class Profile:
    opening_cash: float = 8.0
    monthly_revenue: float = 5.0
    monthly_expenses: float = 4.0
    monthly_debt_service: float = 0.0
    min_reserve: float = 3.0
    collection_lag: int = 0     # months between billing and cash arriving
    horizon: int = 12
    receivables: list = field(default_factory=list)
    history: list = field(default_factory=list)  # monthly cash history for MC gate


@dataclass
class Decision:
    label: str = "Buy equipment"
    amount: float = 4.0


@dataclass
class Scenario:
    name: str = "adverse"
    revenue_shock_pct: float = -0.20   # persistent, from shock_start onward
    shock_start: int = 1
    one_off_shock: float = 1.5
    one_off_month: int = 3


BASE = Scenario("base", 0.0, 1, 0.0, 3)


@dataclass
class Plan:
    id: str
    name: str
    kind: str
    purchase: dict                       # month -> payment
    expense_cut_pct: float = 0.0
    cut_months: int = 0
    extra_cost: float = 0.0              # interest / premium / cut disruption
    goal_curve: list = field(default_factory=list)   # fraction of goal in place, months 0..H
    acquired_month: int = 0
    notes: str = ""


@dataclass
class Forecast:
    cash: np.ndarray
    coll: np.ndarray
    exp: np.ndarray
    purchase: np.ndarray
    shock: np.ndarray
    recv: np.ndarray


def collections(profile: Profile, sc: Scenario) -> np.ndarray:
    """Cash collected per month: revenue billed `lag` months earlier (shock hits billing)."""
    out = np.zeros(profile.horizon + 1)
    for t in range(1, profile.horizon + 1):
        s = t - profile.collection_lag
        f = 1.0 + (sc.revenue_shock_pct if s >= sc.shock_start else 0.0)
        out[t] = profile.monthly_revenue * f
    return out


def forecast(profile: Profile, plan: Plan, sc: Scenario, expected_weight: float = 0.0) -> Forecast:
    H = profile.horizon
    coll = collections(profile, sc)
    cut = np.zeros(H + 1)
    cut[1:min(plan.cut_months, H) + 1] = plan.expense_cut_pct
    exp = np.zeros(H + 1)
    exp[1:] = profile.monthly_expenses * (1 - cut[1:]) + profile.monthly_debt_service
    pur = np.zeros(H + 1)
    for m, a in plan.purchase.items():
        if 0 <= m <= H:
            pur[m] += a
    shock = np.zeros(H + 1)
    if 0 <= sc.one_off_month <= H:
        shock[sc.one_off_month] = sc.one_off_shock
    recv = np.zeros(H + 1)
    for r in profile.receivables:
        if 0 <= r.month <= H:
            recv[r.month] += r.amount * (1.0 if r.confirmed else expected_weight)
    cash = profile.opening_cash + np.cumsum(coll - exp - pur - shock + recv)
    return Forecast(cash, coll, exp, pur, shock, recv)


def risk_report(profile: Profile, plan: Plan, sc: Scenario) -> dict:
    f = forecast(profile, plan, sc)
    R, cash = profile.min_reserve, f.cash
    below = np.where(cash < R - 1e-9)[0]
    neg = np.where(cash < -1e-9)[0]
    mi = int(cash.argmin())
    rep = {
        "scenario": sc.name, "passes": len(below) == 0,
        "min_cash": round(float(cash[mi]), 2), "min_month": mi,
        "breach_month": int(below[0]) if len(below) else None,
        "shortfall": round(float(max(0.0, R - cash[mi])), 2),
        "runway_months": int(neg[0]) if len(neg) else None,   # first month cash < 0
        "cash": [round(float(x), 2) for x in cash],
    }
    if len(below):
        b = int(below[0])
        base_coll = collections(profile, BASE)
        rep["causes"] = {
            "purchase_paid": round(float(f.purchase[:b + 1].sum()), 2),
            "revenue_loss": round(float((base_coll - f.coll)[:b + 1].sum()), 2),
            "one_off_shock": round(float(f.shock[:b + 1].sum()), 2),
        }
        def ok(p, s): return forecast(profile, p, s).cash.min() >= R - 1e-9
        tests = {"purchase": ok(replace(plan, purchase={}), sc),
                 "revenue_shock": ok(plan, replace(sc, revenue_shock_pct=0.0)),
                 "one_off_shock": ok(plan, replace(sc, one_off_shock=0.0))}
        rep["single_fixes"] = [k for k, v in tests.items() if v]
    return rep


def as_is_plan(decision: Decision) -> Plan:
    return Plan("as_is", f"{decision.label} now (as planned)", "as_is", {0: decision.amount},
                goal_curve=None, notes="Original decision, no changes")


def diagnose(profile: Profile, decision: Decision, sc: Scenario) -> dict:
    p = as_is_plan(decision)
    base, adv = risk_report(profile, p, BASE), risk_report(profile, p, sc)
    return {"decision": {"label": decision.label, "amount": decision.amount},
            "reserve": profile.min_reserve, "base": base, "adverse": adv,
            "looks_safe_then_fails": base["passes"] and not adv["passes"]}
