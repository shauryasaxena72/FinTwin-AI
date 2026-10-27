from dataclasses import replace

from data import (
    Inflow,
    Loan,
    Plan,
    Profile,
    Scenario,
    Tagged,
    parse_csv_rows,
    validate_month_coverage,
)
from cashflow import forecast
from risk import assess_risk
from scenarios import baseline_scenario, with_payment_delay, with_revenue_drop


def t(value, tag="fixture", source="hand-calculated fixture"):
    return Tagged(value=value, tag=tag, source=source)


def base_inputs():
    profile = Profile(
        opening_cash=t(100),
        reserve=t(20),
        monthly_opex=t(30),
        horizon_months=t(3),
        inflows=t(
            (
                Inflow(
                    amount=t(60),
                    due_month=t(1),
                    status=t("confirmed"),
                    category=t("revenue"),
                    actual_pay_month=t(1),
                    expected_pay_month=t(None),
                    customer=t("A"),
                ),
                Inflow(
                    amount=t(30),
                    due_month=t(1),
                    status=t("expected"),
                    category=t("revenue"),
                    actual_pay_month=t(None),
                    expected_pay_month=t(1),
                    customer=t("B"),
                ),
            )
        ),
        loans=t(
            (
                Loan(
                    monthly_payment=t(10),
                    start_month=t(2),
                    end_month=t(3),
                    label=t("Term loan"),
                ),
            )
        ),
    )
    plan = Plan(
        name=t("No purchase"),
        purchase_amount=t(0),
        purchase_month=t(1),
        monthly_opex_reduction=t(0),
        reduction_start_month=t(1),
        reduction_end_month=t(0),
    )
    return profile, plan, baseline_scenario()


def test_hand_calculated_cash_path_and_strict_receipts():
    profile, plan, scenario = base_inputs()
    rows = forecast(profile, plan, scenario)
    assert [row.closing_cash for row in rows] == [130, 90, 50]
    inclusive_rows = forecast(profile, plan, scenario, strict=False)
    assert [row.closing_cash for row in inclusive_rows] == [160, 120, 80]


def test_scenario_delays_and_revenue_shock_change_receipt_month_and_amount():
    profile, plan, scenario = base_inputs()
    delayed = forecast(profile, plan, with_payment_delay(scenario, 1))
    assert [row.confirmed_receipts for row in delayed] == [0, 60, 0]
    shocked = forecast(profile, plan, with_revenue_drop(scenario, 0.5))
    assert shocked[0].confirmed_receipts == 30


def test_risk_reports_breach_shortfall_type_runway_and_counterfactual():
    _, plan, scenario = base_inputs()
    profile = Profile(
        opening_cash=t(40),
        reserve=t(20),
        monthly_opex=t(20),
        horizon_months=t(1),
        inflows=t(()),
        loans=t(()),
    )
    scenario = replace(
        scenario,
        one_off_shock_amount=t(21),
    )
    report = assess_risk(profile, plan, scenario)
    assert report["first_breach_month"] == 1
    assert report["max_shortfall"] == 21
    assert report["breach_type"] == "PERSISTENT"
    assert report["runway_month"] == 1
    assert "one_off_shock" in report["clearing_counterfactuals"]


def test_temporary_breach_recognizes_recovery():
    profile, plan, scenario = base_inputs()
    profile = Profile(
        opening_cash=t(30),
        reserve=t(20),
        monthly_opex=t(25),
        horizon_months=t(2),
        inflows=t(
            (
                Inflow(
                    amount=t(40),
                    due_month=t(2),
                    status=t("confirmed"),
                    category=t("other"),
                    actual_pay_month=t(2),
                    expected_pay_month=t(None),
                    customer=t("A"),
                ),
            )
        ),
        loans=t(()),
    )
    report = assess_risk(profile, plan, scenario)
    assert report["breach_type"] == "TEMPORARY"
    assert report["first_breach_month"] == 1


def test_validation_rejects_reserve_above_cash_and_missing_months():
    profile, _, _ = base_inputs()
    invalid = Profile(
        opening_cash=t(10),
        reserve=t(20),
        monthly_opex=profile.monthly_opex,
        horizon_months=profile.horizon_months,
        inflows=profile.inflows,
        loans=profile.loans,
    )
    try:
        forecast(invalid, base_inputs()[1], baseline_scenario())
    except ValueError as error:
        assert "reserve cannot be greater" in str(error)
    else:
        raise AssertionError("Expected reserve validation to fail.")
    try:
        validate_month_coverage([1, 3], 3)
    except ValueError as error:
        assert "missing month(s): 2" in str(error)
    else:
        raise AssertionError("Expected missing-month validation to fail.")


def test_csv_classification_is_a_suggestion_until_confirmed():
    rows = parse_csv_rows(
        'description,amount\nCustomer invoice #12,"1,200"\n',
        "invoices.csv",
    )
    assert rows[0].category_suggestion == "revenue"
    assert rows[0].amount == 1200
    assert rows[0].review_required is True
    assert rows[0].confirmed is False
