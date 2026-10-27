"""Narrator module: all text built only from results.json fields.

Every screen, the memo, and the copilot call narrator functions.
Each function takes case.results and returns text built only from its fields.
A test fails if any number in the text is not present in results.json.
"""
from __future__ import annotations


def explain_risk(results: dict) -> str:
    """Explain risk from results.json. No numbers outside results."""
    risk = results.get("risk", {})
    profile = results.get("profile", {})
    reserve = profile.get("reserve", "N/A")
    first_breach = risk.get("first_breach_month")
    max_shortfall = risk.get("max_shortfall", 0)
    kind = risk.get("kind", "NONE")

    if first_breach is None:
        return f"No reserve breach detected. Reserve: {reserve}."

    causes = risk.get("causes", [])
    fixes = [c.get("driver") for c in causes if c.get("removal_clears_breach")]

    text = (
        f"Risk: {kind} breach. First breach month: {first_breach}. "
        f"Max shortfall: {max_shortfall}. Reserve: {reserve}."
    )
    if fixes:
        text += f" Removing any of [{', '.join(fixes)}] alone would avoid the breach."
    return text


def explain_plan(plan: dict) -> str:
    """Explain a plan from results.json. No numbers outside results."""
    name = plan.get("name", "Unknown plan")
    cost = plan.get("cost", 0)
    delay = plan.get("delay_months", 0)
    breach_prob = plan.get("breach_prob")
    min_cash = plan.get("min_cash", 0)
    label = plan.get("label", "")

    text = f"Plan: {name}. Extra cost: {cost}. Goal acquired month: {delay}. Min cash: {min_cash}."
    if breach_prob is not None:
        text += f" Breach probability: {breach_prob}."
    if label:
        text += f" Label: {label}."
    return text


def explain_rejection(plan: dict) -> str:
    """Explain why a plan was rejected. No numbers outside results."""
    name = plan.get("name", "Unknown plan")
    reason = plan.get("reject_reason", "unknown")
    return f"Plan '{name}' was rejected: {reason}."


def explain_scenario(results: dict) -> str:
    """Explain scenario results from results.json. No numbers outside results."""
    mc = results.get("mc", {})
    enabled = mc.get("enabled", False)
    risk = results.get("risk", {})
    kind = risk.get("kind", "NONE")
    first_breach = risk.get("first_breach_month")

    text = f"Scenario: {kind} breach."
    if first_breach is not None:
        text += f" First breach month: {first_breach}."
    if enabled:
        text += f" Monte Carlo: N={mc.get('N', 0)}, seed={mc.get('seed', 0)}."
        bands = mc.get("bands", {})
        if bands.get("p50"):
            text += f" Median path available."
    else:
        text += f" Monte Carlo disabled: {mc.get('disabled_reason', 'unknown')}."
    return text


def memo(results: dict) -> str:
    """One-page decision memo from results.json. All text from results only."""
    risk = results.get("risk", {})
    profile = results.get("profile", {})
    plans = results.get("plans", [])
    mc = results.get("mc", {})

    lines = ["=== DECISION MEMO ===", ""]
    lines.append(f"Reserve: {profile.get('reserve', 'N/A')}")
    lines.append(f"Risk: {risk.get('kind', 'NONE')}")
    if risk.get("first_breach_month") is not None:
        lines.append(f"First breach month: {risk['first_breach_month']}")
        lines.append(f"Max shortfall: {risk.get('max_shortfall', 0)}")
    lines.append("")
    lines.append(f"Feasible plans: {len([p for p in plans if p.get('feasible')])}")
    if plans:
        best = [p for p in plans if p.get("feasible")]
        if best:
            best = sorted(best, key=lambda p: p.get("score", 999))[0]
            lines.append(f"Recommended: {best.get('name', 'N/A')}")
            lines.append(f"  Extra cost: {best.get('extra_cost', 0)}")
            lines.append(f"  Min cash (stress): {best.get('min_cash_stress', 0)}")
    lines.append("")
    lines.append(f"Monte Carlo: {'enabled' if mc.get('enabled') else 'disabled'}")
    if mc.get("disabled_reason"):
        lines.append(f"  Reason: {mc['disabled_reason']}")
    lines.append("")
    lines.append("Disclaimer: Forecasts are decision support, not financial advice.")
    return "\n".join(lines)
