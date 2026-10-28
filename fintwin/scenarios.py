"""Scenario construction and comparison helpers."""

from __future__ import annotations

from dataclasses import replace

from data import Scenario, Tagged


def with_payment_delay(scenario: Scenario, months: int) -> Scenario:
    if months < 0:
        raise ValueError("Payment delay cannot be negative.")
    return replace(
        scenario,
        payment_delay_months=replace(
            scenario.payment_delay_months,
            value=months,
            tag="scenario_override",
        ),
    )


def with_revenue_drop(scenario: Scenario, fraction: float) -> Scenario:
    if not 0 <= fraction <= 1:
        raise ValueError("Revenue drop must be between 0 and 1.")
    return replace(
        scenario,
        revenue_drop_fraction=replace(
            scenario.revenue_drop_fraction,
            value=fraction,
            tag="scenario_override",
        ),
    )


def baseline_scenario(source: str = "user_input") -> Scenario:
    def tagged(value, tag="user_input"):
        return Tagged(value=value, tag=tag, source=source)

    return Scenario(
        name=tagged("Baseline"),
        revenue_drop_fraction=tagged(0.0),
        revenue_drop_start_month=tagged(1),
        payment_delay_months=tagged(0),
        one_off_shock_amount=tagged(0.0),
        one_off_shock_month=tagged(1),
    )
