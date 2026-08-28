"""Baseline Severity Classification Rules and Category Mappings."""
from typing import Tuple

from app.utils.constants import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    SEVERITY_INFO,
    CATEGORY_SECURITY,
    CATEGORY_SYNTAX,
    CATEGORY_LOGIC,
    CATEGORY_RESOURCE_LEAK,
    CATEGORY_CONCURRENCY,
    CATEGORY_TYPE_ERROR,
    CATEGORY_COMPLEXITY,
    CATEGORY_STYLE,
)


def get_rule_baseline_severity(category: str, rule_id: str, message: str) -> Tuple[str, float]:
    """Determine baseline severity level (Critical/High/Medium/Low/Info) and numeric score (0-100)."""
    msg_lower = message.lower()
    rule_lower = rule_id.lower()

    # Critical: Direct exploitability, SQLi, command injection, hardcoded auth secrets
    if category == CATEGORY_SECURITY:
        if any(k in msg_lower or k in rule_lower for k in ["sql", "injection", "command", "exec", "hardcoded", "password", "secret", "token", "b602", "b605", "b105", "b106"]):
            return SEVERITY_CRITICAL, 95.0
        return SEVERITY_HIGH, 80.0

    # High: Infinite loops, crash risks, resource leaks, concurrency race conditions
    if category in (CATEGORY_RESOURCE_LEAK, CATEGORY_CONCURRENCY):
        return SEVERITY_HIGH, 82.0

    if category == CATEGORY_SYNTAX:
        return SEVERITY_HIGH, 85.0

    if category in (CATEGORY_LOGIC, CATEGORY_TYPE_ERROR):
        if "zerodivision" in msg_lower or "infinite loop" in msg_lower or "unhandled" in msg_lower:
            return SEVERITY_HIGH, 78.0
        if "mutable default" in msg_lower or "off-by-one" in msg_lower or "unreachable" in msg_lower:
            return SEVERITY_MEDIUM, 60.0
        return SEVERITY_MEDIUM, 55.0

    # Medium: High cyclomatic complexity, unhandled edge cases
    if category == CATEGORY_COMPLEXITY:
        return SEVERITY_MEDIUM, 50.0

    # Low / Info: Style, naming, spacing, minor PEP8 conventions
    if category == CATEGORY_STYLE:
        if any(k in rule_lower for k in ["c0103", "c0301", "e501", "w291", "w293"]):
            return SEVERITY_INFO, 15.0
        return SEVERITY_LOW, 30.0

    return SEVERITY_LOW, 35.0
