"""Tagged financial inputs and conservative CSV ingestion helpers."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

T = TypeVar("T")

InflowStatus = Literal["confirmed", "expected"]
RowCategory = Literal["revenue", "opex", "loan", "other"]


@dataclass(frozen=True)
class Tagged(Generic[T]):
    value: T
    tag: str
    source: str


@dataclass(frozen=True)
class Inflow:
    amount: Tagged[float]
    due_month: Tagged[int]
    status: Tagged[InflowStatus]
    category: Tagged[RowCategory]
    actual_pay_month: Tagged[int | None]
    expected_pay_month: Tagged[int | None]
    customer: Tagged[str]


@dataclass(frozen=True)
class Loan:
    monthly_payment: Tagged[float]
    start_month: Tagged[int]
    end_month: Tagged[int]
    label: Tagged[str]


@dataclass(frozen=True)
class Plan:
    name: Tagged[str]
    purchase_amount: Tagged[float]
    purchase_month: Tagged[int]
    monthly_opex_reduction: Tagged[float]
    reduction_start_month: Tagged[int]
    reduction_end_month: Tagged[int]


@dataclass(frozen=True)
class Scenario:
    name: Tagged[str]
    revenue_drop_fraction: Tagged[float]
    revenue_drop_start_month: Tagged[int]
    payment_delay_months: Tagged[int]
    one_off_shock_amount: Tagged[float]
    one_off_shock_month: Tagged[int]


@dataclass(frozen=True)
class Profile:
    opening_cash: Tagged[float]
    reserve: Tagged[float]
    monthly_opex: Tagged[float]
    horizon_months: Tagged[int]
    inflows: Tagged[tuple[Inflow, ...]]
    loans: Tagged[tuple[Loan, ...]]


@dataclass(frozen=True)
class ClassifiedRow:
    row_number: int
    description: str
    amount: float
    category_suggestion: RowCategory
    review_required: bool = True
    confirmed: bool = False


def validate_profile(profile: Profile) -> None:
    """Raise a plain-language ValueError for invalid forecast inputs."""
    for label, amount in (
        ("Opening cash", profile.opening_cash.value),
        ("Reserve", profile.reserve.value),
        ("Monthly operating expenses", profile.monthly_opex.value),
    ):
        if amount < 0:
            raise ValueError(f"{label} cannot be negative.")
    if profile.reserve.value > profile.opening_cash.value:
        raise ValueError("The reserve cannot be greater than opening cash.")
    if profile.horizon_months.value < 1:
        raise ValueError("Forecast horizon must include at least one month.")
    for inflow in profile.inflows.value:
        if inflow.amount.value < 0:
            raise ValueError("Inflow amounts cannot be negative.")
        if inflow.due_month.value < 1:
            raise ValueError("Inflow due months must be month 1 or later.")
        pay_month = (
            inflow.actual_pay_month.value
            if inflow.status.value == "confirmed"
            else inflow.expected_pay_month.value
        )
        if pay_month is None:
            status = inflow.status.value
            raise ValueError(f"A {status} inflow is missing its pay month.")
        if pay_month < 1:
            raise ValueError("Inflow pay months must be month 1 or later.")
    for loan in profile.loans.value:
        if loan.monthly_payment.value < 0:
            raise ValueError("Loan payments cannot be negative.")
        if loan.start_month.value < 1 or loan.end_month.value < loan.start_month.value:
            raise ValueError("Loan payment months must be a valid inclusive range.")


def validate_month_coverage(months: list[int], horizon: int) -> None:
    """Reject missing months in an uploaded history instead of silently filling gaps."""
    missing = sorted(set(range(1, horizon + 1)) - set(months))
    if missing:
        month_list = ", ".join(str(month) for month in missing)
        raise ValueError(f"Uploaded history is missing month(s): {month_list}.")


def suggest_category(description: str) -> RowCategory:
    """Suggest a category using transparent keyword rules; never confirms a row."""
    text = description.casefold()
    if any(word in text for word in ("loan", "emi", "repayment", "interest")):
        return "loan"
    if any(word in text for word in ("invoice", "customer", "sales", "receipt", "payment received")):
        return "revenue"
    if any(word in text for word in ("rent", "salary", "utilities", "subscription", "supplier")):
        return "opex"
    return "other"


def parse_csv_rows(content: str | bytes, source: str) -> list[ClassifiedRow]:
    """Parse bank-statement or invoice CSV rows into unconfirmed review suggestions."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError(f"{source} has no CSV header row.")

    fields = {name.casefold().strip(): name for name in reader.fieldnames if name}
    description_field = next(
        (fields[key] for key in ("description", "details", "narration", "customer", "vendor") if key in fields),
        None,
    )
    amount_field = next((fields[key] for key in ("amount", "value", "total") if key in fields), None)
    if description_field is None or amount_field is None:
        raise ValueError(f"{source} must include a description and amount column.")

    rows: list[ClassifiedRow] = []
    for row_number, row in enumerate(reader, start=2):
        description = (row.get(description_field) or "").strip()
        raw_amount = (row.get(amount_field) or "").strip().replace(",", "")
        if not description or not raw_amount:
            raise ValueError(f"{source}, row {row_number}: description and amount are required.")
        try:
            amount = abs(float(raw_amount))
        except ValueError as error:
            raise ValueError(f"{source}, row {row_number}: amount must be a number.") from error
        rows.append(
            ClassifiedRow(
                row_number=row_number,
                description=description,
                amount=amount,
                category_suggestion=suggest_category(description),
            )
        )
    return rows
