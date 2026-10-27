"""UI kit: shared components for Streamlit screens.

Theme, provenance badge, plan card, chart helpers.
All numbers come from results.json — UI never computes finance numbers.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go

# --- Theme ---
THEME = {
    "primary": "#1d6b58",
    "danger": "#c93d2f",
    "warning": "#d98b1f",
    "success": "#2f8a5b",
    "muted": "#6b7380",
    "bg": "#f8f5ee",
    "card": "#fdfbf6",
    "border": "#ddd7c8",
}

TAG_COLORS = {
    "UPLOAD": "#2e4e9a",
    "ENTERED": "#1d6b58",
    "DERIVED": "#b0489a",
    "EXTERNAL": "#d0702a",
    "ASSUMPTION": "#6b7380",
}


def provenance_badge(tag: str, source: str = "") -> str:
    """Return HTML for a provenance badge."""
    color = TAG_COLORS.get(tag, "#6b7380")
    tooltip = f" title='{source}'" if source else ""
    return f'<span style="background:{color};color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;"{tooltip}>{tag}</span>'


def plan_card(plan: dict, selected: bool = False) -> None:
    """Render a plan card in Streamlit."""
    border = "2px solid #1d6b58" if selected else "1px solid #ddd7c8"
    label = plan.get("pareto_label") or ""
    label_html = f'<span style="background:#1d6b58;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{label}</span>' if label else ""
    st.markdown(f"""
    <div style="border:{border};border-radius:8px;padding:12px;margin:4px 0;background:#fdfbf6;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong>{plan.get('name', 'Unnamed')}</strong>
            {label_html}
        </div>
        <div style="font-size:13px;color:#6b7380;margin-top:4px;">
            Score: {plan.get('score', 'N/A')} | Min cash: {plan.get('min_cash', 'N/A')} |
            Breach prob: {plan.get('breach_prob', 'N/A')} | Cost: {plan.get('cost', 'N/A')}
        </div>
    </div>
    """, unsafe_allow_html=True)


def cash_flow_chart(series: dict, reserve: float, mc_bands: dict | None = None) -> go.Figure:
    """Create a Plotly cash flow chart with reserve line and optional MC fan."""
    fig = go.Figure()
    x = list(range(len(series.get("months", []))))

    if "base" in series:
        fig.add_scatter(x=x, y=series["base"].get("closing", []), name="Base", line=dict(color="#1d6b58"))
    if "adverse" in series:
        fig.add_scatter(x=x, y=series["adverse"].get("closing", []), name="Adverse", line=dict(color="#c93d2f"))

    for plan_id, plan_series in series.items():
        if plan_id in ("base", "adverse"):
            continue
        fig.add_scatter(x=x, y=plan_series.get("closing", []), name=plan_id[:30])

    fig.add_hline(y=reserve, line_dash="dash", annotation_text="Min reserve", line_color="#c93d2f")

    if mc_bands and mc_bands.get("p10") and mc_bands.get("p90"):
        fig.add_scatter(x=x, y=mc_bands["p90"], fill=None, mode="lines", line=dict(width=0), showlegend=False)
        fig.add_scatter(x=x, y=mc_bands["p10"], fill="tonexty", mode="lines", line=dict(width=0),
                       fillcolor="rgba(29,107,88,0.15)", name="MC p10-p90")

    fig.update_layout(xaxis_title="Month", yaxis_title="Cash (Rs lakh)", height=430, template="plotly_white")
    return fig


def empty_state(missing: list[str]) -> None:
    """Show empty/insufficient-data state with exactly what's missing."""
    st.warning("Insufficient data to run analysis.")
    st.markdown("**Missing:**")
    for item in missing:
        st.markdown(f"- {item}")
    st.markdown("Please provide the missing inputs above.")


def assumptions_panel(assumptions: list[str]) -> None:
    """Render an assumptions panel."""
    with st.expander("Assumptions"):
        for a in assumptions:
            st.markdown(f"- {a}")


def disclaimer_footer() -> None:
    """Render disclaimer footer."""
    st.caption("Forecasts are decision support, not financial advice. Uploaded rows are never auto-trusted.")
