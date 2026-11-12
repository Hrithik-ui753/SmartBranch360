"""Unit tests for Report Generator and CLI workflow."""

import json
from assurance_engine.validator import ValidationFinding
from assurance_engine.reporter import AssuranceReportGenerator


def test_reporter_health_score_calculation():
    # 2 passes, 1 warning, 0 failures -> score should be 100 - 3 = 97
    pass_finding = ValidationFinding(status="PASS", code="P1", category="Cat", message="Passed")
    warn_finding = ValidationFinding(status="WARNING", code="W1", category="Cat", message="Warning")
    reporter = AssuranceReportGenerator(
        site_name="TestSite",
        plan_findings=[pass_finding],
        assurance_findings=[pass_finding],
        security_findings=[warn_finding]
    )
    assert reporter.health_score == 97
    assert reporter.pass_count == 2
    assert reporter.warn_count == 1
    assert reporter.fail_count == 0


def test_reporter_json_generation():
    pass_finding = ValidationFinding(status="PASS", code="P1", category="Cat", message="Passed")
    reporter = AssuranceReportGenerator(
        site_name="TestSite",
        plan_findings=[pass_finding],
        assurance_findings=[],
        security_findings=[]
    )
    json_str = reporter.generate_json()
    data = json.loads(json_str)
    assert data["site"] == "TestSite"
    assert data["health_score"] == 100
    assert data["metrics"]["passed"] == 1


def test_reporter_html_generation():
    pass_finding = ValidationFinding(status="PASS", code="P1", category="Cat", message="Passed")
    reporter = AssuranceReportGenerator(
        site_name="TestSite",
        plan_findings=[pass_finding],
        assurance_findings=[],
        security_findings=[]
    )
    html_str = reporter.generate_html()
    assert "<!DOCTYPE html>" in html_str
    assert "SmartBranch360 Network Assurance Report" in html_str
    assert "TestSite" in html_str

