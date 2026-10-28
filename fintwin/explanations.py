
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


class GroundingError(ValueError):
    pass


@dataclass(frozen=True)
class Evidence:
    field: str
    value: object
    rendered: str


@dataclass(frozen=True)
class Explanation:
    text: str
    evidence: tuple[Evidence, ...]


NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z])[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?"
)


def normalize_number(value):
    value = str(value).replace(",", "").replace("%", "")

    try:
        return Decimal(value).normalize()
    except InvalidOperation as exc:
        raise GroundingError(
            f"Invalid numeric value: {value}"
        ) from exc


def check_grounding(text, evidence):
    expected = Counter(
        normalize_number(item.rendered)
        for item in evidence
    )

    actual = Counter(
        normalize_number(match.group())
        for match in NUMBER_PATTERN.finditer(text)
    )

    if actual != expected:
        unsupported = actual - expected
        missing = expected - actual

        raise GroundingError(
            f"Unsupported numeric claims: {list(unsupported.elements())}; "
            f"unused evidence values: {list(missing.elements())}"
        )


def explain_diagnosis(dx):
    try:
        reserve = dx["reserve"]
        base = dx["base"]
        adverse = dx["adverse"]
        label = dx["decision"]["label"]

        values = [
            ("decision.label", label),
            ("reserve", reserve),
            ("base.min_cash", base["min_cash"]),
            ("adverse.min_cash", adverse["min_cash"]),
        ]

        if not adverse["passes"]:
            values.extend([
                ("adverse.min_month", adverse["min_month"]),
                ("adverse.breach_month", adverse["breach_month"]),
                ("adverse.shortfall", adverse["shortfall"]),
            ])

        evidence = []
        rendered = {}

        for field, value in values:
            if isinstance(value, bool) or value is None:
                raise GroundingError(
                    f"Missing or invalid value for {field}"
                )

            if field.endswith("label"):
                rendered[field] = str(value)
                continue

            if not isinstance(value, (int, float, Decimal)):
                raise GroundingError(
                    f"Expected a numeric value for {field}"
                )

            if not Decimal(str(value)).is_finite():
                raise GroundingError(
                    f"Non-finite value for {field}"
                )

            display = (
                str(value)
                if field.endswith("month")
                else f"{value:.2f}"
            )

            evidence.append(Evidence(field, value, display))
            rendered[field] = display

        text = (
            f"Decision: {label}. "
            f"In the base scenario, minimum cash is Rs "
            f"{rendered['base.min_cash']} lakh. "
            f"The required reserve is Rs "
            f"{rendered['reserve']} lakh. "
        )

        if adverse["passes"]:
            text += (
                "The plan remains above the reserve in the "
                "adverse scenario, with minimum cash of Rs "
                f"{rendered['adverse.min_cash']} lakh."
            )
        else:
            text += (
                "The plan breaches the reserve in the adverse "
                "scenario. Minimum cash is Rs "
                f"{rendered['adverse.min_cash']} lakh in month "
                f"{rendered['adverse.min_month']}. "
                "The first breach occurs in month "
                f"{rendered['adverse.breach_month']}, "
                "with a shortfall of Rs "
                f"{rendered['adverse.shortfall']} lakh."
            )

        result = Explanation(text, tuple(evidence))
        check_grounding(result.text, result.evidence)
        return result

    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, GroundingError):
            raise
        raise GroundingError(
            f"Could not generate a grounded explanation: {exc}"
        ) from exc
