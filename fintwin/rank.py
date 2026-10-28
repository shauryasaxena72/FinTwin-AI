"""Pareto ranking: rank plans on (delay, cost, breach probability)."""
from __future__ import annotations
import numpy as np
from engine.core import Profile, Plan, Scenario
from montecarlo import monte_carlo
from generate import hard_filter

LABEL_FASTEST = "Fastest safe"
LABEL_SAFEST = "Safest"
LABEL_CHEAPEST = "Cheapest"

DEFAULT_WEIGHTS = {"cost": 0.3, "goal_loss": 0.3, "risk": 0.4}


def rank_plans(profile: Profile, d, sc: Scenario, weights: dict | None = None,
               top_n: int = 3, n_mc: int = 5000) -> dict:
    """Rank feasible plans. Returns dict with ranked, all_feasible, counts."""
    from generate import generate_candidates
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    cands = generate_candidates(profile, d)
    surv, rejected = [], 0
    for p in cands:
        feasible, reason = hard_filter(profile, p, sc)
        if feasible:
            surv.append(p)
        else:
            rejected += 1
    rows = []
    for p in surv:
        rep = None
        from engine.core import risk_report
        rep = risk_report(profile, p, sc)
        mc = monte_carlo(profile, p, sc, n=n_mc)
        rows.append({"id": p.id, "name": p.name, "kind": p.kind, "cost": round(p.extra_cost, 2),
                     "goal_loss": round(1 - float(np.mean(p.goal_curve)) if p.goal_curve else 0, 3),
                     "acquired_month": p.acquired_month,
                     "breach_prob": mc.get("breach_prob", mc.get("breach_probability")),
                     "min_cash": rep["min_cash"], "min_month": rep["min_month"],
                     "buffer_over_reserve": round(rep["min_cash"] - profile.min_reserve, 2),
                     "purchase_schedule": {int(k): round(v, 2) for k, v in p.purchase.items()},
                     "expense_cut": f"{int(p.expense_cut_pct*100)}% for {p.cut_months} mo" if p.cut_months else "none",
                     "notes": p.notes, "cash_path": rep["cash"], "p5_path": mc.get("p5_path", [])})
    # normalise
    for key in ("cost", "goal_loss", "breach_prob"):
        v = np.array([r[key] for r in rows], float) if rows else np.array([])
        span = v.max() - v.min() if len(v) and v.max() != v.min() else 0
        for r, x in zip(rows, v):
            r["n_" + key] = 0.0 if span == 0 else float((x - v.min()) / span)
    for r in rows:
        r["score"] = round(w["cost"] * r["n_cost"] + w["goal_loss"] * r["n_goal_loss"] + w["risk"] * r["n_breach_prob"], 3)
    rows.sort(key=lambda r: (r["score"], r["breach_prob"], r["cost"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    for r in rows:
        for k in ("n_cost", "n_goal_loss", "n_breach_prob"):
            r.pop(k, None)
    # Pareto labels
    if rows:
        fastest = min(rows, key=lambda r: (r["acquired_month"], r["score"]))
        safest = min(rows, key=lambda r: (r["breach_prob"], r["score"]))
        cheapest = min(rows, key=lambda r: (r["cost"], r["score"]))
        for r in rows:
            r["pareto_label"] = None
        fastest["pareto_label"] = LABEL_FASTEST
        safest["pareto_label"] = LABEL_SAFEST
        cheapest["pareto_label"] = LABEL_CHEAPEST
    return {"weights": w, "n_candidates": len(cands), "n_feasible": len(rows),
            "n_rejected": rejected, "ranked": rows[:top_n], "all_feasible": rows}
