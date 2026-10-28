"""Narrator backend: generate plain-language memo from results."""

from __future__ import annotations

from typing import Any


def generate_memo(results: Any) -> str:
    """Produce a grounded memo string from results dict/dataclass."""
    if isinstance(results, dict):
        ranked = results.get("ranked", [])
        if not ranked:
            return "No feasible plans found."
        best = ranked[0]
        return f"Recommended plan: {best.get('name', 'N/A')}. Trade-offs: {best.get('reason', '')}"
    return "Results unavailable."
