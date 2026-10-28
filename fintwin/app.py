"""Small Streamlit interface for reviewed financial inputs and cash-flow risk."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from cashflow import forecast
from data import (
    Inflow,
    Loan,
    Plan,
    Profile,
    Tagged,
    parse_csv_rows,
    validate_profile,
)
from risk import assess_risk
from scenarios import baseline_scenario


def tagged(value, source: str, tag: str = "user_input"):
    return Tagged(value=value, tag=tag, source=source)


st.set_page_config(page_title="FinTwin AI", page_icon="💸", layout="wide")
st.title("FinTwin AI — cash-flow twin")
st.caption("Forecasts are decision support, not financial advice. Uploaded rows are never auto-trusted.")

with st.sidebar:
    st.header("Sample data")
    sample = st.selectbox("Load sample scenario", ["Manual", "Green (Healthy)", "Red (Stressed)", "Mixed (Borderline)"])

    SAMPLES = {
        "Green (Healthy)": {"opening_cash": 200000.0, "reserve": 30000.0, "monthly_opex": 50000.0, "horizon": 6, "loan_payment": 8000.0, "revenue_drop": 0, "delay_months": 0},
        "Red (Stressed)": {"opening_cash": 50000.0, "reserve": 30000.0, "monthly_opex": 40000.0, "horizon": 6, "loan_payment": 8000.0, "revenue_drop": 20, "delay_months": 2},
        "Mixed (Borderline)": {"opening_cash": 100000.0, "reserve": 30000.0, "monthly_opex": 45000.0, "horizon": 6, "loan_payment": 8000.0, "revenue_drop": 10, "delay_months": 1},
    }

    if sample in SAMPLES:
        s = SAMPLES[sample]
        opening_cash = s["opening_cash"]
        reserve = s["reserve"]
        monthly_opex = s["monthly_opex"]
        horizon = s["horizon"]
        loan_payment = s["loan_payment"]
        revenue_drop = s["revenue_drop"]
        delay_months = s["delay_months"]
        st.info(f"Loaded {sample} sample. Adjust values below or run forecast.")
    else:
        opening_cash = st.number_input("Opening cash", min_value=0.0, value=10000.0)
        reserve = st.number_input("Minimum reserve", min_value=0.0, value=3000.0)
        monthly_opex = st.number_input("Monthly operating expenses", min_value=0.0, value=4000.0)
        horizon = st.number_input("Forecast months", min_value=1, max_value=36, value=6)
        loan_payment = st.number_input("Monthly loan payment", min_value=0.0, value=0.0)
        revenue_drop = st.slider("Revenue drop (%)", min_value=0, max_value=100, value=0)
        delay_months = st.number_input("Payment delay (months)", min_value=0, max_value=12, value=0)

    strict = st.toggle("Strict mode: confirmed receipts only", value=True)

st.subheader("Upload data for review")
bank_file = st.file_uploader("Bank statement CSV", type="csv", key="bank")
invoice_file = st.file_uploader("Invoices CSV", type="csv", key="invoices")
review_rows = []
for uploaded in (bank_file, invoice_file):
    if uploaded is not None:
        try:
            review_rows.extend(parse_csv_rows(uploaded.getvalue(), uploaded.name))
        except (UnicodeDecodeError, ValueError) as error:
            st.error(str(error))

if review_rows:
    st.warning("These are rule-based suggestions only. Confirm classifications before using records.")
    reviewed_rows = st.data_editor(
        [
            {
                "row": row.row_number,
                "description": row.description,
                "amount": row.amount,
                "category": row.category_suggestion,
                "confirmed": row.confirmed,
            }
            for row in review_rows
        ],
        disabled=["row", "description", "amount"],
        column_config={
            "category": st.column_config.SelectboxColumn(
                "Category", options=["revenue", "opex", "loan", "other"]
            ),
            "confirmed": st.column_config.CheckboxColumn("Confirmed by user"),
        },
        use_container_width=True,
    )
    if not all(row["confirmed"] for row in reviewed_rows):
        st.info("Confirm every uploaded row before treating it as reviewed.")

st.subheader("Forecast inputs")
st.info("Add confirmed and expected receipts below. Uploaded classifications require human review and are not included automatically.")
receipt_count = st.number_input("Number of receipts to enter", min_value=0, max_value=30, value=1)
receipts = []
for index in range(int(receipt_count)):
    cols = st.columns(4)
    amount = cols[0].number_input(f"Receipt {index + 1} amount", min_value=0.0, key=f"amount-{index}")
    month = cols[1].number_input(f"Pay month {index + 1}", min_value=1, max_value=int(horizon), value=1, key=f"month-{index}")
    status = cols[2].selectbox(f"Status {index + 1}", ["confirmed", "expected"], key=f"status-{index}")
    category = cols[3].selectbox(f"Type {index + 1}", ["revenue", "other"], key=f"category-{index}")
    receipts.append((amount, int(month), status, category))

if st.button("Run forecast", type="primary"):
    source = "manual user input"
    inflows = tuple(
        Inflow(
            amount=tagged(amount, source),
            due_month=tagged(month, source),
            status=tagged(status, source),
            category=tagged(category, source),
            actual_pay_month=tagged(month if status == "confirmed" else None, source),
            expected_pay_month=tagged(month if status == "expected" else None, source),
            customer=tagged(f"Receipt {index + 1}", source),
        )
        for index, (amount, month, status, category) in enumerate(receipts)
    )
    loans = ()
    if loan_payment:
        loans = (
            Loan(
                monthly_payment=tagged(loan_payment, source),
                start_month=tagged(1, source),
                end_month=tagged(int(horizon), source),
                label=tagged("Loan payment", source),
            ),
        )
    profile = Profile(
        opening_cash=tagged(opening_cash, source),
        reserve=tagged(reserve, source),
        monthly_opex=tagged(monthly_opex, source),
        horizon_months=tagged(int(horizon), source),
        inflows=tagged(inflows, source),
        loans=tagged(loans, source),
    )
    plan = Plan(
        name=tagged("As entered", source),
        purchase_amount=tagged(0.0, source),
        purchase_month=tagged(1, source),
        monthly_opex_reduction=tagged(0.0, source),
        reduction_start_month=tagged(1, source),
        reduction_end_month=tagged(0, source),
    )
    scenario = baseline_scenario(source)
    scenario = replace(
        scenario,
        revenue_drop_fraction=tagged(revenue_drop / 100, source),
        payment_delay_months=tagged(int(delay_months), source),
    )
    try:
        validate_profile(profile)
        results = forecast(profile, plan, scenario, strict=strict)
        report = assess_risk(profile, plan, scenario, strict=strict)
    except ValueError as error:
        st.error(str(error))
    else:
        latest_cash = results[-1].closing_cash
        first_breach = report["first_breach_month"]
        metrics = st.columns(4)
        metrics[0].metric("Closing cash", f"{latest_cash:,.2f}")
        metrics[1].metric("Reserve", f"{reserve:,.2f}")
        metrics[2].metric("Maximum shortfall", f"{report['max_shortfall']:,.2f}")
        metrics[3].metric("Runway", str(report["runway_month"] or "Beyond horizon"))
        if first_breach is None:
            st.success("No reserve breach in the forecast.")
        else:
            st.error(f"{report['breach_type'].title()} reserve breach first occurs in month {first_breach}.")
        st.dataframe(
            [
                {
                    "month": item.month,
                    "opening cash": item.opening_cash,
                    "confirmed receipts": item.confirmed_receipts,
                    "expected receipts": item.expected_receipts,
                    "operating expenses": item.operating_expenses,
                    "loan payments": item.loan_payments,
                    "closing cash": item.closing_cash,
                }
                for item in results
            ],
            use_container_width=True,
        )
        st.caption("Provenance: manually entered assumptions; no uploaded row is treated as confirmed.")
