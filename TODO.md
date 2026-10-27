# FinTwin AI — Task Tracker

## Done

- [x] Initialize Git repository
- [x] Add all project files (source code, tests, dashboard, demo, presentation)
- [x] Create initial commit and push to GitHub
- [x] Install Python dependencies (numpy, plotly, streamlit, pandas, pytest, anthropic)
- [x] Run tests — 10/10 passed
- [x] Run CLI demo successfully
- [x] Launch Streamlit dashboard at http://localhost:8501
- [x] Create 4 role assignment files (role_1 through role_4)
- [x] Create project README with structure, quick start, team roles, shared contract, build order
- [x] Reduce build timeline from 30 to 24 hours
- [x] Add .gitignore for __pycache__, .pytest_cache, generated artifacts, IDE, OS, env files
- [x] Push all changes to GitHub (https://github.com/shauryasaxena72/FinTwin-AI)

## To Do

### Step 1 — Immediate Setup
- [ ] Assign 4 owners to vertical slices (A: Data & Risk, B: Plans, C: Uncertainty & Lab, D: Product & Story)
- [ ] Verify repo at https://github.com/shauryasaxena72/FinTwin-AI looks correct

### Step 2 — Owner D Critical Path (Hours 0–3)
- [ ] Publish `engine/contract.py` with `results.json` schema as Python dataclasses
- [ ] Create `Case` state in `st.session_state["case"]` (`profile`, `scenario`, `results`, `selected_plan`, `selected_month`)
- [ ] Build `ui_kit.py` (provenance badge, plan card, chart helpers, theme)
- [ ] Create `narrator.py` skeleton with function signatures
- [ ] Create stub `results.json` so all screens render on day one

### Step 3 — Walking Skeleton (Hours 0–6)
- [ ] All 4 owners add screens reading the stub `results.json`
- [ ] Full loop clickable: upload → plan cards → Scenario Lab → memo
- [ ] Stubs labelled "stub" (only place stubs are allowed)

### Step 4 — Full Real-Data Loop (Hours 6–12)
- [ ] Each owner replaces stub with real engine function
- [ ] Merge daily to `main`
- [ ] Run full loop on one real uploaded file at sync points (hours 6, 12, 16)

### Step 5 — Polish & Demo (Hours 12–24)
- [ ] Monte Carlo + confirmed/expected toggle (Owner C)
- [ ] Copilot v1 with dropdown questions (Owner D)
- [ ] Fallback recording, Q&A sheet, pitch deck with cited statistics
- [ ] Bugfix and rehearse

### Step 6 — If Fewer Than 4 People
- [ ] Merge Modeling (A) with Simulation (B)
- [ ] Merge Frontend (C) with AI & Demo (D)

## Sync Points
- **Hour 6, 12, 16**: All four sit together, run the full loop on one real file, fix whatever breaks before anything new is added.

## Review Pairing
- A reviews B, B reviews A (data to plans)
- C reviews D, D reviews C (lab to story)
- Nobody merges into `main` without a buddy who has run it
