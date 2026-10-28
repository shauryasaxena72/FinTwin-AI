"""Learned customer payment delays: simple moving average from history."""

from __future__ import annotations

from typing import List


def learn_delay(history: List[int]) -> float:
    """Learn average payment delay from historical pay-month offsets."""
    if not history:
        return 0.0
    return sum(history) / len(history)


def predict_pay_month(due_month: int, learned_delay: float) -> int:
    """Predict pay month given due month and learned delay."""
    return due_month + int(round(learned_delay))
