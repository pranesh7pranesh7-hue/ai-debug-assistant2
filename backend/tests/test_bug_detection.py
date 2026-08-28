"""Tests for Bug Detection and Deduplication."""
import pytest
from app.modules.bug_detection.patterns import find_pattern_bugs
from app.modules.bug_detection.deduper import deduplicate_bugs
from app.modules.bug_detection.detector import detect_all_bugs


def test_pattern_detector_catches_infinite_loop():
    code = "while True:\n    x = 1"
    bugs = find_pattern_bugs(code)
    assert any(b["rule_id"] == "BUG-PAT-004" for b in bugs)


def test_pattern_detector_catches_sql_injection():
    code = "def query(user_id):\n    sql = f'SELECT * FROM users WHERE id = {user_id}'\n    return sql"
    bugs = find_pattern_bugs(code)
    assert any(b["rule_id"] == "BUG-PAT-006" for b in bugs)


def test_deduplicator_removes_identical_line_findings():
    findings = [
        {"line": 5, "column": 0, "tool": "bandit", "rule_id": "B608", "category": "security", "message": "SQL Injection"},
        {"line": 5, "column": 0, "tool": "flake8", "rule_id": "F401", "category": "security", "message": "SQL Injection"},
    ]
    deduped = deduplicate_bugs(findings)
    assert len(deduped) == 1
    assert deduped[0]["tool"] == "bandit"


@pytest.mark.asyncio
async def test_detect_all_bugs_end_to_end():
    code = "def test_func(a, b=[]):\n    f = open('leak.txt')\n    return b"
    bugs, metrics = await detect_all_bugs(code)
    assert len(bugs) >= 2
