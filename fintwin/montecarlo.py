"""Vectorised Monte Carlo. Common random numbers (same seed) so plans are compared fairly.
Enabled only with sufficient history (gate: 12 months). N=5000 default (~0.7pp SE)."""
from __future__ import annotations
import numpy as np
from engine.core import Profile, Plan, Scenario
from simulate import simulate


HISTORY_GATE = 12  # months of history required to enable Monte Carlo


def _has_sufficient_history(profile: Profile) -> bool:
    """Check if profile has enough history to enable Monte Carlo.
    If no history is provided (empty/None), MC runs in legacy mode (enabled)."""
    history = getattr(profile, "history", None)
    if not history:
        return True  # backward compat: no history provided => run MC
    return len(history) >= HISTORY_GATE


def monte_carlo(profile: Profile, plan: Plan, sc: Scenario, n: int = 5000, seed: int = 7,
                rev_vol: float = 0.10, exp_vol: float = 0.05, shock_prob: float = 0.5,
                enabled: bool | None = None) -> dict:
    """Run Monte Carlo simulation. Returns dict with breach_prob, CI, bands, etc.

    If history is insufficient, returns disabled result with reason.
    """
    if enabled is None:
        enabled = _has_sufficient_history(profile)

    if not enabled:
        return {
            "enabled": False,
            "disabled_reason": f"Insufficient history (need {HISTORY_GATE} months, "
                               f"have {len(getattr(profile, 'history', []) or [])})",
            "N": 0, "seed": seed,
            "breach_prob": None, "breach_probability": None,
            "ci": None, "bands": {"p10": [], "p50": [], "p90": []},
            "p5_path": [],
        }

    cash = simulate(profile, plan, sc, n=n, seed=seed, rev_vol=rev_vol,
                    exp_vol=exp_vol, shock_prob=shock_prob)
    min_cash_per_path = cash.min(axis=1)
    breach = (min_cash_per_path < profile.min_reserve - 1e-9)

    # 95% CI for breach probability
    p_hat = float(breach.mean())
    se = np.sqrt(p_hat * (1 - p_hat) / n)
    ci_low = max(0.0, p_hat - 1.96 * se)
    ci_high = min(1.0, p_hat + 1.96 * se)

    return {
        "enabled": True,
        "disabled_reason": None,
        "N": n, "seed": seed,
        "breach_prob": round(p_hat, 3),
        "breach_probability": round(p_hat, 3),
        "ci": [round(ci_low, 4), round(ci_high, 4)],
        "bands": {
            "p10": [round(float(x), 2) for x in np.percentile(cash, 10, axis=0)],
            "p50": [round(float(x), 2) for x in np.percentile(cash, 50, axis=0)],
            "p90": [round(float(x), 2) for x in np.percentile(cash, 90, axis=0)],
        },
        "p5_path": [round(float(x), 2) for x in np.percentile(cash, 5, axis=0)],
        "p5_min_cash": round(float(np.percentile(min_cash_per_path, 5)), 2),
        "median_min_cash": round(float(np.median(min_cash_per_path)), 2),
        "runs": n,
    }
