"""Alternative-plan generator -> feasibility filter -> Monte Carlo -> weighted ranking."""
from __future__ import annotations
import numpy as np
from .engine import Profile, Decision, Scenario, Plan, as_is_plan, risk_report
from .montecarlo import monte_carlo

DEFAULT_WEIGHTS = {"cost": 0.3, "goal_loss": 0.3, "risk": 0.4}
CUT_PAIN = 0.5          # disruption cost per rupee of expense cut (exposed assumption)
LOAN_RATE = 0.12        # annual, installment financing


def _curve(H, pay, P):
    cum = np.cumsum([pay.get(m, 0.0) for m in range(H + 1)]) / P
    return [round(float(x), 3) for x in np.minimum(cum, 1.0)]


def _structures(profile: Profile, d: Decision) -> list:
    H, P, out = profile.horizon, d.amount, []
    out.append(as_is_plan(d))
    out[-1].goal_curve = [1.0] * (H + 1)
    for k in range(1, 7):                                   # delay
        out.append(Plan(f"delay{k}", f"Delay {d.label.lower()} {k} mo", "delay", {k: P},
                        goal_curve=[0.0] * k + [1.0] * (H + 1 - k), acquired_month=k))
    for n in (2, 3, 4):                                     # phase
        for s in (1, 2, 3):
            pay = {i * s: P / n for i in range(n)}
            if max(pay) <= H:
                out.append(Plan(f"phase{n}x{s}", f"Phase in {n} tranches every {s} mo", "phase", pay,
                                goal_curve=_curve(H, pay, P), acquired_month=max(pay)))
    for down in (0.3, 0.4, 0.5):                            # installments
        for n in (3, 6, 9):
            bal, r, pay, interest = P * (1 - down), LOAN_RATE / 12, {0: P * down}, 0.0
            for m in range(1, n + 1):
                i = bal * r; interest += i; pay[m] = (P * (1 - down)) / n + i; bal -= (P * (1 - down)) / n
            out.append(Plan(f"inst{int(down*100)}x{n}", f"{int(down*100)}% down + {n} installments",
                            "installments", pay, extra_cost=round(interest, 3), goal_curve=[1.0] * (H + 1),
                            notes=f"{LOAN_RATE:.0%} p.a. financing"))
    for lag in (2, 3):                                      # negotiated supplier credit
        out.append(Plan(f"credit{lag}", f"Negotiate: 50% now, 50% after {lag} mo (+2% price)", "negotiate",
                        {0: P * 0.5, lag: P * 0.5 + P * 0.02}, extra_cost=round(P * 0.02, 3),
                        goal_curve=[1.0] * (H + 1), notes="Assumes supplier accepts"))
    return out


def generate_candidates(profile: Profile, d: Decision) -> list:
    cands = []
    for s in _structures(profile, d):
        cands.append(s)
        if s.kind == "as_is":
            continue
        for pct, months in ((0.10, 3), (0.10, 6), (0.15, 3), (0.15, 6)):    # cash-flow-first overlay
            savings = profile.monthly_expenses * pct * months
            cands.append(Plan(f"{s.id}+cut{int(pct*100)}x{months}", f"{s.name} + cut costs {int(pct*100)}% for {months} mo",
                              "hybrid", dict(s.purchase), pct, months, round(s.extra_cost + CUT_PAIN * savings, 3),
                              s.goal_curve, s.acquired_month, s.notes))
    return cands


def rank_plans(profile: Profile, d: Decision, sc: Scenario, weights: dict | None = None,
               top_n: int = 3, n_mc: int = 1000) -> dict:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    cands = generate_candidates(profile, d)
    surv, rejected = [], 0
    for p in cands:
        rep = risk_report(profile, p, sc)
        if rep["passes"]: surv.append((p, rep))
        else: rejected += 1
    rows = []
    for p, rep in surv:
        mc = monte_carlo(profile, p, sc, n=n_mc)
        rows.append({"id": p.id, "name": p.name, "kind": p.kind, "cost": round(p.extra_cost, 2),
                     "goal_loss": round(1 - float(np.mean(p.goal_curve)), 3), "acquired_month": p.acquired_month,
                     "breach_prob": mc["breach_prob"], "min_cash": rep["min_cash"], "min_month": rep["min_month"],
                     "buffer_over_reserve": round(rep["min_cash"] - profile.min_reserve, 2),
                     "purchase_schedule": {int(k): round(v, 2) for k, v in p.purchase.items()},
                     "expense_cut": f"{int(p.expense_cut_pct*100)}% for {p.cut_months} mo" if p.cut_months else "none",
                     "notes": p.notes, "cash_path": rep["cash"], "p5_path": mc["p5_path"]})
    for key in ("cost", "goal_loss", "breach_prob"):
        v = np.array([r[key] for r in rows], float)
        span = v.max() - v.min() if len(v) else 0
        for r, x in zip(rows, v): r["n_" + key] = 0.0 if span == 0 else float((x - v.min()) / span)
    for r in rows:
        r["score"] = round(w["cost"] * r["n_cost"] + w["goal_loss"] * r["n_goal_loss"] + w["risk"] * r["n_breach_prob"], 3)
    rows.sort(key=lambda r: (r["score"], r["breach_prob"], r["cost"]))
    for i, r in enumerate(rows, 1): r["rank"] = i
    for r in rows:
        for k in ("n_cost", "n_goal_loss", "n_breach_prob"): r.pop(k)
    return {"weights": w, "n_candidates": len(cands), "n_feasible": len(rows), "n_rejected": rejected,
            "ranked": rows[:top_n], "all_feasible": rows}
