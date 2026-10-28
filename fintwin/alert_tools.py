"""Alert tools backend: threshold-based alerts on cash, inflows, and risk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

@dataclass
class Alert:
    severity: str
    message: str
    metric: str
    value: float
    threshold: float

def check_cash_alerts(profile: Any, threshold: float = 0.0) -> list[Alert]:
    alerts = []
    closing = profile.opening_cash.value + sum(i.amount.value for i in profile.inflows.value) - profile.monthly_opex.value * profile.horizon_months.value
    if closing < threshold:
        alerts.append(Alert("critical", f"Closing cash {closing:.2f} below threshold {threshold:.2f}", "closing_cash", closing, threshold))
    if closing < profile.reserve.value:
        alerts.append(Alert("warning", f"Closing cash {closing:.2f} below reserve {profile.reserve.value:.2f}", "reserve", closing, profile.reserve.value))
    return alerts

def check_inflow_alerts(profile: Any) -> list[Alert]:
    alerts = []
    for i in profile.inflows.value:
        if i.status.value == "expected" and i.expected_pay_month.value is None:
            alerts.append(Alert("warning", f"Expected inflow missing pay month", "inflow_pay_month", 0.0, 0.0))
    return alerts

def run_all_alerts(profile: Any) -> list[dict]:
    alerts = check_cash_alerts(profile) + check_inflow_alerts(profile)
    return [a.__dict__ for a in alerts]
