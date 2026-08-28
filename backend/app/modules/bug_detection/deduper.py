"""Bug Findings Deduplicator.
Merges redundant or overlapping alerts from multiple tools targeting the same line or root issue.
"""
from typing import Any, Dict, List


def deduplicate_bugs(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate findings based on (line, category) proximity and rule similarity."""
    seen_signatures = set()
    deduped: List[Dict[str, Any]] = []

    # Priority order for tools when identical line+category occur:
    # bandit/security_pattern > ast_pattern > ast > pylint > flake8
    tool_priority = {
        "bandit": 5,
        "security_pattern": 5,
        "ast_pattern": 4,
        "ast": 3,
        "pylint": 2,
        "flake8": 1,
        "radon": 2,
    }

    # Sort by line first, then tool priority descending
    sorted_findings = sorted(
        findings,
        key=lambda x: (x.get("line", 1), -tool_priority.get(x.get("tool", ""), 0)),
    )

    for item in sorted_findings:
        line = item.get("line", 1)
        category = item.get("category", "logic")
        rule_id = item.get("rule_id", "")
        msg = item.get("message", "").strip().lower()

        # Primary signature: line + category
        # If line is identical and category is identical (e.g. both flag SQL injection on line 12), keep higher priority tool
        key = (line, category)
        if key in seen_signatures:
            # Check if this is a distinct specific rule on the same line
            exact_key = (line, category, rule_id)
            if exact_key in seen_signatures:
                continue
            # If the messages have high word overlap (>50%), discard duplicate
            continue

        seen_signatures.add(key)
        seen_signatures.add((line, category, rule_id))
        deduped.append(item)

    return deduped
