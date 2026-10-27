# FinTwin AI — React Frontend

Responsive React + Vite dashboard for FinTwin AI. This folder lives alongside the existing Python engine and prototype.

## Current behavior and honest limitations

- Starts on the business overview and does not preload financial results.
- Accepts a bank statement CSV and invoices CSV, then shows imported rows for explicit classification and confirmation.
- Includes vendor quote and loan offer fields. Blank values remain blank; the browser does not calculate loan costs or financial metrics.
- Overview, Digital Twin, Scenario Lab, plan explorer, and grounded copilot are implemented with empty states when engine results are missing.
- API mode is disabled by default. No demo financial figures are bundled or generated.
- CSV parsing in this starter is intentionally lightweight and does not handle every CSV edge case (such as quoted commas). Replace it with a proper CSV parser or the backend's ingestion response before production use.
- The endpoint names and payloads in `src/services/api.js` are integration placeholders. Agree the final contract with the engine team before enabling API mode.

## Requirements

- Node.js 20 LTS or newer recommended
- npm
- Git

## Run locally

```bash
cd fintwin-frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

Windows PowerShell copy alternative:

```powershell
Copy-Item .env.example .env
```

## Build check

```bash
npm run build
npm run preview
```

## Connect the backend

1. Start the backend using the team's documented instructions.
2. Confirm API routes, fields, error formats, and CORS settings with the engine owner.
3. Update `src/services/api.js` paths and payload fields to match the actual API.
4. Copy `.env.example` to `.env` and set:

```dotenv
VITE_USE_API=true
VITE_API_BASE_URL=http://localhost:8000
```

5. Restart Vite after changing `.env`.
6. The expected result payload currently follows this frontend-facing shape (contract proposal, not a claim about existing backend output):

```json
{
  "metrics": {
    "current_cash": 0,
    "monthly_surplus": 0,
    "runway_months": null
  },
  "reserve": 0,
  "reserve_tag": "engine result",
  "cashflow": [
    {
      "month": "YYYY-MM",
      "opening_cash": 0,
      "inflow": 0,
      "expected_inflow": 0,
      "outflow": 0,
      "closing_cash": 0,
      "breach": false,
      "plan_name": "Original plan"
    }
  ],
  "risk": {
    "breach": false,
    "first_breach_month": null,
    "max_shortfall": 0,
    "kind": null
  },
  "plans": [],
  "rejected_plans": [],
  "mc": { "enabled": false }
}
```

The numeric zeros above document the *shape only*; they are not seeded values. Do not return this example as a real response. Omit missing metrics or return `null`, and the UI will show an unavailable marker.

### API placeholders

- `POST /api/v1/intake` — multipart upload plus reviewed classification rows; expected to return results or an intake status.
- `GET /api/v1/results` — return the latest `results.json`-equivalent payload.
- `POST /api/v1/scenario` — accept stress controls and return re-simulated results.
- `POST /api/v1/copilot` — return a grounded explanation with evidence/provenance.

These routes are proposals only. They are not confirmed to exist in the current repository.

## Public deployment

The repository deploys this frontend to GitHub Pages from `master` using `.github/workflows/deploy-frontend.yml`. Vite is configured for the repository URL prefix.

After the Pages workflow completes, the public dashboard URL is:
https://shauryasaxena72.github.io/FinTwin-AI/

The GitHub repository must have Pages enabled with the source set to **GitHub Actions**. The first deployment may require an administrator to enable this in **Settings → Pages**.

## Main files

- `src/App.jsx` — navigation, screen composition, empty states, result wiring
- `src/pages/Intake.jsx` — file selection, quote/loan forms, row review
- `src/components/Plot.jsx` — Plotly cash-flow visualization (only renders a chart when engine data exists)
- `src/components/Sidebar.jsx` — navigation and product shell
- `src/services/api.js` — isolated backend adapter placeholders
- `src/styles.css` — responsive fintech design system
