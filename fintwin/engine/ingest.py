"""CSV ingestion and row classification for FinTwin AI backend.

Parses bank statements and invoices, suggests categories via keyword rules.
Never auto-trusts — all rows flagged for user review.
"""
from __future__ import annotations

import csv
import io
from data import ClassifiedRow, RowCategory, suggest_category


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


def validate_month_coverage(months: list[int], horizon: int) -> None:
    """Reject missing months in an uploaded history instead of silently filling gaps."""
    missing = sorted(set(range(1, horizon + 1)) - set(months))
    if missing:
        month_list = ", ".join(str(month) for month in missing)
        raise ValueError(f"Uploaded history is missing month(s): {month_list}.")
