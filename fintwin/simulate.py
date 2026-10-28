"""Vectorised simulation: simulate(plan, scenario, profile) over many paths with NumPy.
No Python loops over paths."""
from __future__ import annotations
import numpy as np
from engine.core import Profile, Plan, Scenario


def simulate(profile: Profile, plan: Plan, sc: Scenario, n: int = 5000, seed: int = 7,
            rev_vol: float = 0.10, exp_vol: float = 0.05, shock_prob: float = 0.5,
            late_pay_prob: float = 0.2) -> np.ndarray:
    """Return cash paths array of shape (n, horizon+1). Fully vectorised over paths."""
    rng = np.random.default_rng(seed)
    H, T = profile.horizon, profile.horizon + 1
    z_rev = rng.standard_normal((n, T))
    z_exp = rng.standard_normal((n, T))
    u_shock = rng.random(n)
    u_recv = rng.random((n, max(1, len(profile.receivables))))
    jitter = rng.random((n, max(1, len(profile.receivables)))) < late_pay_prob

    # base flow per path
    flow = np.zeros((n, T))
    for t in range(1, T):
        s = t - profile.collection_lag
        mean_rev = profile.monthly_revenue * (1.0 + (sc.revenue_shock_pct if s >= sc.shock_start else 0.0))
        cut = plan.expense_cut_pct if t <= plan.cut_months else 0.0
        rev = np.maximum(0.0, mean_rev * (1.0 + rev_vol * z_rev[:, t]))
        exp = profile.monthly_expenses * (1.0 - cut) * (1.0 + exp_vol * z_exp[:, t]) + profile.monthly_debt_service
        flow[:, t] = rev - exp

    # purchase payments
    for m, a in plan.purchase.items():
        if 0 <= m <= H:
            flow[:, m] -= a

    # one-off shock (probabilistic)
    if 0 <= sc.one_off_month <= H:
        shock_mask = (u_shock < shock_prob).astype(float)
        flow[:, sc.one_off_month] -= sc.one_off_shock * shock_mask

    # receivables
    for i, r in enumerate(profile.receivables):
        paid = np.ones(n, dtype=bool) if r.confirmed else (u_recv[:, i] < r.p_pay)
        m_arr = np.where(jitter[:, i], r.month + 1, r.month)
        valid = paid & (m_arr >= 0) & (m_arr <= H)
        # vectorised scatter-add
        idx = np.where(valid)[0]
        months = m_arr[valid].astype(int)
        np.add.at(flow, (idx, months), r.amount)

    cash = profile.opening_cash + np.cumsum(flow, axis=1)
    return cash
