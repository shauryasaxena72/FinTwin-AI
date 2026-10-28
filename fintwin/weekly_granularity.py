"""Weekly/daily granularity: sub-monthly cash flow breakdown."""

from __future__ import annotations

from typing import Any, List


def weekly_cashflow(monthly_revenue: float, monthly_expenses: float, weeks: int = 4) -> List[float]:
    """Split monthly cash flow into weekly buckets."""
    rev_w = monthly_revenue / weeks
    exp_w = monthly_expenses / weeks
    return [rev_w - exp_w] * weeks


def daily_cashflow(monthly_revenue: float, monthly_expenses: float, days: int = 30) -> List[float]:
    """Split monthly cash flow into daily buckets."""
    rev_d = monthly_revenue / days
    exp_d = monthly_expenses / days
    return [rev_d - exp_d] * days
