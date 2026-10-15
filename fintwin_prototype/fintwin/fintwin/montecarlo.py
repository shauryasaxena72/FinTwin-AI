"""Vectorised Monte Carlo. Common random numbers (same seed) so plans are compared fairly."""
from __future__ import annotations
import numpy as np
from .engine import Profile, Plan, Scenario


def monte_carlo(profile: Profile, plan: Plan, sc: Scenario, n: int = 1000, seed: int = 7,
                rev_vol: float = 0.10, exp_vol: float = 0.05, shock_prob: float = 0.5) -> dict:
    rng = np.random.default_rng(seed)
    H, T = profile.horizon, profile.horizon + 1
    z_rev, z_exp = rng.standard_normal((n, T)), rng.standard_normal((n, T))
    u_shock = rng.random(n)
    u_recv = rng.random((n, max(1, len(profile.receivables))))
    jitter = rng.random((n, max(1, len(profile.receivables)))) < 0.2   # 20%: paid one month late

    flow = np.zeros((n, T))
    for t in range(1, T):
        s = t - profile.collection_lag
        mean = profile.monthly_revenue * (1 + (sc.revenue_shock_pct if s >= sc.shock_start else 0.0))
        cut = plan.expense_cut_pct if t <= plan.cut_months else 0.0
        rev = np.maximum(0.0, mean * (1 + rev_vol * z_rev[:, t]))
        exp = profile.monthly_expenses * (1 - cut) * (1 + exp_vol * z_exp[:, t]) + profile.monthly_debt_service
        flow[:, t] = rev - exp
    for m, a in plan.purchase.items():
        if m <= H:
            flow[:, m] -= a
    if 0 <= sc.one_off_month <= H:
        flow[:, sc.one_off_month] -= sc.one_off_shock * (u_shock < shock_prob)
    for i, r in enumerate(profile.receivables):
        paid = np.ones(n, bool) if r.confirmed else (u_recv[:, i] < r.p_pay)
        m = np.where(jitter[:, i], r.month + 1, r.month)
        for k in range(n):
            if paid[k] and 0 <= m[k] <= H:
                flow[k, m[k]] += r.amount
    cash = profile.opening_cash + np.cumsum(flow, axis=1)
    breach = (cash.min(axis=1) < profile.min_reserve - 1e-9)
    return {"runs": n, "breach_prob": round(float(breach.mean()), 3),
            "p5_min_cash": round(float(np.percentile(cash.min(axis=1), 5)), 2),
            "median_min_cash": round(float(np.median(cash.min(axis=1))), 2),
            "p50_path": [round(float(x), 2) for x in np.percentile(cash, 50, axis=0)],
            "p5_path": [round(float(x), 2) for x in np.percentile(cash, 5, axis=0)]}
