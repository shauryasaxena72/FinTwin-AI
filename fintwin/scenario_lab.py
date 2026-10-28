"""Scenario Lab backend: what-if parameter sweeps and sensitivity analysis."""

from __future__ import annotations

from typing import Any, Callable, List, Dict


def sweep(profile: Any, param: str, values: List[float], fn: Callable[[Any, float], Any]) -> List[Dict]:
    """Run a function over a range of parameter values, return list of results."""
    results = []
    for v in values:
        r = fn(profile, v)
        results.append({"param": param, "value": v, "result": r})
    return results


def sensitivity(profile: Any, base_result: float, deltas: Dict[str, float]) -> Dict[str, float]:
    """Compute sensitivity of a result to small parameter changes."""
    out = {}
    for k, d in deltas.items():
        out[k] = d  # placeholder: caller supplies delta impact
    return out
