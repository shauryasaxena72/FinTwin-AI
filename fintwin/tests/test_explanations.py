
import pytest

from explanations import (
    GroundingError,
    check_grounding,
    explain_diagnosis,
)


@pytest.fixture
def diagnosis_result():
    return {
        "decision": {
            "label": "Buy equipment",
            "amount": 4.0,
        },
        "reserve": 3.0,
        "base": {
            "scenario": "base",
            "passes": True,
            "min_cash": 4.0,
            "min_month": 1,
            "breach_month": None,
            "shortfall": 0.0,
            "runway_months": None,
            "cash": [4, 5, 6, 7, 8, 9, 10],
        },
        "adverse": {
            "scenario": "adverse",
            "passes": False,
            "min_cash": 2.5,
            "min_month": 3,
            "breach_month": 3,
            "shortfall": 0.5,
            "runway_months": None,
            "cash": [4, 4, 4, 2.5, 2.5, 2.5],
        },
        "looks_safe_then_fails": True,
    }


def test_explanation_uses_engine_fields(diagnosis_result):
    result = explain_diagnosis(diagnosis_result)

    assert "Buy equipment" in result.text
    assert "2.50" in result.text
    assert "0.50" in result.text
    assert "month 3" in result.text

    check_grounding(result.text, result.evidence)


def test_invented_number_is_rejected(diagnosis_result):
    result = explain_diagnosis(diagnosis_result)

    tampered = result.text + " The loss will be Rs 47.30 lakh."

    with pytest.raises(GroundingError):
        check_grounding(tampered, result.evidence)


def test_changed_number_is_rejected(diagnosis_result):
    result = explain_diagnosis(diagnosis_result)

    tampered = result.text.replace("2.50", "99.90", 1)

    with pytest.raises(GroundingError):
        check_grounding(tampered, result.evidence)


def test_missing_required_field_is_rejected(diagnosis_result):
    del diagnosis_result["adverse"]["min_cash"]

    with pytest.raises(GroundingError):
        explain_diagnosis(diagnosis_result)


def test_passing_stress_case_uses_safe_template(diagnosis_result):
    diagnosis_result["adverse"]["passes"] = True

    result = explain_diagnosis(diagnosis_result)

    assert "remains above the reserve" in result.text
    assert "first breach occurs" not in result.text

    check_grounding(result.text, result.evidence)
