"""Tests for Severity Classification Module."""
import pytest
from app.modules.severity.severity_rules import get_rule_baseline_severity
from app.modules.severity.classifier import SeverityClassifier


def test_security_rule_baseline_is_critical():
    sev, score = get_rule_baseline_severity("security", "B608", "Hardcoded SQL injection vulnerability")
    assert sev == "Critical"
    assert score >= 90.0


def test_style_rule_baseline_is_low_or_info():
    sev, score = get_rule_baseline_severity("style", "C0103", "Variable name doesn't conform to snake_case")
    assert sev in ("Low", "Info")
    assert score <= 35.0


@pytest.mark.asyncio
async def test_severity_classifier_output():
    sev, score = await SeverityClassifier.classify_bug(
        code_context="def func(): pass",
        category="security",
        rule_id="B608",
        message="SQL injection",
        line=1,
        use_llm=False,
    )
    assert sev in ["Critical", "High", "Medium", "Low", "Info"]
    assert 0.0 <= score <= 100.0
