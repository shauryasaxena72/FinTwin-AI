"""Bank/accounting feeds: auto-ingest CSV, classify rows."""

from __future__ import annotations

from data import parse_csv_rows, suggest_category
from typing import Any, List


def ingest_bank_feed(content: str, source: str = "bank") -> List[Any]:
    """Parse a bank statement CSV into classified rows."""
    return parse_csv_rows(content, source)


def classify_rows(rows: List[Any]) -> List[Any]:
    """Return rows with category suggestions (already in ClassifiedRow)."""
    return rows
