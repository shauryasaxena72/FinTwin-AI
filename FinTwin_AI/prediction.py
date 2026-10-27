"""Transparent historical payment-delay estimate; no synthetic history is generated."""

from __future__ import annotations

from datetime import date
from statistics import median


def estimate_median_days_late(
    paid_invoices: list[tuple[date, date]],
) -> int | None:
    """Return median days late from (due_date, paid_date) pairs, or None without data."""
    if not paid_invoices:
        return None
    delays = [(paid - due).days for due, paid in paid_invoices]
    return int(round(median(delays)))
