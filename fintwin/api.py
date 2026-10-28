"""FastAPI backend connecting FinTwin engine to React frontend."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="FinTwin AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")

@app.get("/")
def read_root():
    return {"message": "FinTwin-AI API is running successfully!"}

@app.get("/api/v1/results")
def get_results():
    return {"metrics": {}, "risk": {}, "cashflow": [], "plans": [], "rejected_plans": []}

class ScenarioIn(BaseModel):
    revenueDrop: float = 0
    paymentDelayDays: int = 0
    shockAmount: float = 0
    shockMonth: str = ""

@app.post("/api/v1/scenario")
def run_scenario(scenario: ScenarioIn):
    return {"metrics": {}, "risk": {}, "cashflow": [], "plans": [], "rejected_plans": []}

class CopilotIn(BaseModel):
    question: str

@app.post("/api/v1/copilot")
def ask_copilot(body: CopilotIn):
    from copilot import FinTwinAgent
    agent = FinTwinAgent()
    return {"answer": agent.chat(body.question)}

@app.post("/api/v1/intake")
async def intake(
    bank_statement: UploadFile = File(None),
    invoices: UploadFile = File(None),
    vendor_quote: str = "",
    loan_offer: str = "",
    classifications: str = "",
):
    import io
    bank_content = await bank_statement.read() if bank_statement else b""
    inv_content = await invoices.read() if invoices else b""
    # Parse bank statement
    rows = []
    try:
        from data import parse_csv_rows
        rows = parse_csv_rows(bank_content.decode("utf-8-sig"), "bank")
    except Exception:
        pass
    total_in = sum(r.amount for r in rows if r.amount > 0)
    total_out = sum(r.amount for r in rows if r.amount < 0)
    opening = 0.0
    for r in rows:
        if "opening" in r.description.lower():
            opening = r.amount
    closing = opening + total_in + total_out
    results = {
        "metrics": {
            "current_cash": opening,
            "monthly_surplus": (total_in + total_out) / 12 if total_in + total_out else 0,
            "runway_months": 12.0,
        },
        "reserve": 50000.0,
        "risk": {"breach": closing < 50000, "first_breach_month": None, "max_shortfall": max(0, 50000 - closing), "kind": "none"},
        "cashflow": [{"month": 1, "opening_cash": opening, "inflow": total_in, "outflow": abs(total_out), "closing_cash": closing, "breach": closing < 50000}],
        "plans": [],
        "rejected_plans": [],
    }
    return {"results": results}

@app.get("/api/v1/samples")
def list_samples():
    files = [f for f in os.listdir(SAMPLES_DIR) if f.endswith(".csv")]
    return {"files": files}

@app.get("/api/v1/samples/{filename}")
def download_sample(filename: str):
    path = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename, media_type="text/csv")

@app.post("/api/v1/classify")
async def classify(bank_statement: UploadFile = File(None)):
    content = await bank_statement.read() if bank_statement else b""
    try:
        from data import parse_csv_rows
        rows = parse_csv_rows(content.decode("utf-8-sig"), "bank")
        return {"rows": [{"row_number": r.row_number, "description": r.description, "amount": r.amount, "category": r.category_suggestion, "status": "confirmed"} for r in rows]}
    except Exception as e:
        return {"rows": [], "error": str(e)}

@app.get("/api/v1/sample/{scenario}")
def get_sample(scenario: str):
    """Return sample data for a given scenario (green, mixed, red, blue, amber)."""
    import csv, io
    bank_path = os.path.join(SAMPLES_DIR, f"bank_statement_{scenario}.csv")
    inv_path = os.path.join(SAMPLES_DIR, f"invoices_{scenario}.csv")
    if not os.path.exists(bank_path):
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario}' not found")
    with open(bank_path) as f:
        bank_rows = list(csv.DictReader(f))
    inv_rows = []
    if os.path.exists(inv_path):
        with open(inv_path) as f:
            inv_rows = list(csv.DictReader(f))
    return {"scenario": scenario, "bank_statement": bank_rows, "invoices": inv_rows}

@app.get("/samples", response_class=HTMLResponse)
def samples_page():
    return """<!DOCTYPE html>
<html><head><title>FinTwin Samples</title></head><body>
<h1>Sample Datasets</h1>
<p>Select a scenario to download bank statement + invoices CSV:</p>
<select id="scn" onchange="load()">
  <option value="green">Green (healthy)</option>
  <option value="mixed">Mixed (moderate)</option>
  <option value="red">Red (critical)</option>
  <option value="blue">Blue (high-growth)</option>
  <option value="amber">Amber (startup/low-cash)</option>
</select>
<div id="links"></div>
<script>
function load(){
  const s=document.getElementById('scn').value;
  document.getElementById('links').innerHTML=
    '<a href="/api/v1/samples/bank_statement_'+s+'.csv">Bank Statement</a> | '+
    '<a href="/api/v1/samples/invoices_'+s+'.csv">Invoices</a>';
}
load();
</script>
</body></html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
