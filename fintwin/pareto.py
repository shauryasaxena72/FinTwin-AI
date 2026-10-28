"""Pareto/mixed-integer optimization: multi-objective ranking."""

from __future__ import annotations

from typing import Any, List


def pareto_front(plans: List[Any], objectives: List[str]) -> List[Any]:
    """Return non-dominated plans (Pareto front)."""
    front = []
    for p in plans:
        dominated = False
        for q in plans:
            if p is q:
                continue
            if all(getattr(q, o, 0) >= getattr(p, o, 0) for o in objectives) and any(getattr(q, o, 0) > getattr(p, o, 0) for o in objectives):
                dominated = True
                break
        if not dominated:
            front.append(p)
    return front
