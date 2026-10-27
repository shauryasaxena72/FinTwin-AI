# FinTwin AI — Financial Digital Twin for MSMEs

A financial decision-support system that helps small businesses understand whether they can afford a purchase, find safer alternatives, and stress-test their cash flow against adverse scenarios.

## Project Structure

```
TwinFin/
├── fintwin_prototype/
│   └── fintwin/
│       ├── app.py                 # Streamlit dashboard
│       ├── demo.py                # CLI demo
│       ├── requirements.txt      # Python dependencies
│       ├── README.md             # Prototype-specific docs
│       ├── fintwin/              # Core engine package
│       │   ├── __init__.py
│       │   ├── engine.py         # Profile, Decision, Scenario, diagnose
│       │   ├── montecarlo.py     # Monte Carlo simulation
│       │   ├── planner.py        # Plan generation, filtering, ranking
│       │   └── copilot.py        # Grounded copilot (LLM + offline fallback)
│       └── tests/
│           └── test_fintwin.py   # Hand-calculated fixture tests
├── roles/                       # Role assignment files
│   ├── role_1_frontend_visualization.txt
│   ├── role_2_ai_demo.txt
│   ├── role_3_financial_modeling.txt
│   └── role_4_optimization_simulation.txt
├── todos/                       # Per-role to-do lists
│   ├── todo_role_1_data_risk.txt
│   ├── todo_role_2_plans.txt
│   ├── todo_role_3_uncertainty_lab.txt
│   └── todo_role_4_product_story.txt
└── README.md                     # This file
```

## Quick Start

```bash
# 1. Install dependencies
cd fintwin_prototype/fintwin
pip install -r requirements.txt

# 2. Run tests
python -m pytest tests/ -q

# 3. Run CLI demo
python demo.py

# 4. Launch dashboard
python -m streamlit run app.py
```

The dashboard will be available at http://localhost:8501.

## Optional: LLM Copilot

Set your Anthropic API key for LLM-powered copilot features:
```bash
export ANTHROPIC_API_KEY=your_key_here
```
Without the key, the copilot falls back to a rule-based offline mode.

## Key Assumptions (exposed as constants in engine.py)

| Parameter | Value |
|---|---|
| Currency units | Rs lakh |
| Revenue shock persistence | From month 1 |
| MC revenue volatility | 10% |
| MC expense volatility | 5% |
| One-off shock probability | 50% |
| Loan rate | 12% p.a. |
| Cost-cut disruption cost | 0.5 × savings |
| Optimizer weights | Cost 0.3, Goal-loss 0.3, Risk 0.4 |

## Team Roles

The project is split into 4 vertical slices. Each owner owns their engine functions, Streamlit screen, narrator functions, and tests — shipped together in one PR.

| Owner | Slice | Screens | Engine | Narrator |
|---|---|---|---|---|
| A: Data & Risk | Real data in, breach found | Intake, Overview, Risk card | ingest, twin, risk, cause attribution | explain_risk |
| B: Plans | Safer plans out | Plan cards, rejected list, Pareto | generator, filters, ranking | explain_plan, explain_rejection |
| C: Uncertainty & Lab | Stress and live what-if | Scenario Lab, sliders, toggle | Monte Carlo, vectorized simulate, sensitivity | explain_scenario |
| D: Product & Story | Shell, glue, delivery | App shell, navigation, memo, copilot | case state, contract, integration tests | memo + copilot from A–C functions |

See the `roles/role_*.txt` files for detailed phase breakdowns.

## Shared Contract

All roles read from a single `results.json` object. Key fields:

```json
{
  "provenance": [{"field", "tag": "UPLOAD|ENTERED|DERIVED|EXTERNAL|ASSUMPTION", "source"}],
  "profile": { "cash", "reserve", "opex_by_month[]", "loans[]", "inflows[{amount,month,status}]" },
  "series": { "plan_id": { "scenario_id": { "months[]", "opening[]", "inflow[]", "outflow[]", "closing[]", "drivers[]" } } },
  "risk": { "first_breach_month", "max_shortfall", "kind": "TEMPORARY|PERSISTENT", "causes": [{ "driver", "removal_clears_breach": bool }] },
  "plans": [{ "id", "description", "feasible", "reject_reason", "min_cash_base", "min_cash_stress", "breach_prob", "ci", "delay_months", "extra_cost", "label" }],
  "mc": { "enabled", "disabled_reason", "N", "seed", "bands": { "p10[]", "p50[]", "p90[]" } }
}
```

**Rules:** No number exists without a provenance tag. Nulls are shown as "not available", never replaced with defaults. Month convention: purchases at start of month; `closing_t = closing_{t-1} + inflow_t - outflow_t`; constraint `closing_t >= reserve`.

## Build Order & Sync Points

| Hours | Milestone |
|---|---|
| 0–3 | D publishes contract, Case state, ui_kit, stub results.json. A, B, C each add a screen reading the stub. |
| 3–6 | Walking skeleton: upload → stub → plan cards → lab → memo all render and connect. |
| 6–12 | Each owner replaces stub with real engine function, merging daily. |
| 12–16 | Full real-data loop; D runs click-through checklist. |
| 16–20 | Monte Carlo and toggle land, polish, copilot v1. |
| 20–24 | Bugfix, fallback recording, rehearse. |

Sync points at hours 6, 12, and 16: all four sit together, run the full loop on one real file, fix whatever breaks.

**Pairing for review:** A reviews B, B reviews A (data to plans). C reviews D, D reviews C (lab to story). Nobody merges into `main` without a buddy who has run it.

## License

See [LICENSE](LICENSE) file.
