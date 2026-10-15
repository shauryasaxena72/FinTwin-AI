# FinTwin AI - prototype (Code Yoddhas)

Pipeline from the deck: Inputs -> Digital Twin -> Risk Check -> Alternative Generator -> Simulator + MC -> Optimizer -> Dashboard -> Grounded Copilot.

    pip install -r requirements.txt
    python -m pytest -q          # hand-calculated tests (deck's worked example)
    python demo.py               # CLI demo / demo-day fallback
    streamlit run app.py         # dashboard + copilot
    export ANTHROPIC_API_KEY=... # optional: LLM tool-calling copilot (offline fallback otherwise)

Files: engine.py (twin, risk, root cause) - montecarlo.py - planner.py (generate, filter, rank) - copilot.py (tools, agent, grounding guard) - app.py

Key assumptions (all exposed as constants): units Rs lakh; revenue shock persists from month 1; MC uses 10% revenue / 5% expense volatility and a 50% chance the one-off shock hits; loan rate 12% p.a.; cost-cut disruption cost = 0.5 x savings; weights cost 0.3 / goal-loss 0.3 / risk 0.4.
LLM path (`_llm_chat`) is untested here (no API key in the build sandbox); the offline rule-based path is tested.
