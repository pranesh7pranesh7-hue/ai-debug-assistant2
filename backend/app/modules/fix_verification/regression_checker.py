"""Regression Checker Module.
Compares before-and-after static analysis findings to ensure no new defects were introduced.
"""
from typing import Any, Dict, List, Tuple


class RegressionChecker:
    """Detects regression defects introduced by a candidate patch."""

    @staticmethod
    def check_regressions(
        initial_findings: List[Dict[str, Any]],
        new_findings: List[Dict[str, Any]],
        target_rule_id: str,
    ) -> Tuple[bool, List[str]]:
        """Returns: (has_regressions: bool, regression_reasons: List[str])"""
        reasons: List[str] = []

        # 1. Check for new syntax errors in new_findings
        for f in new_findings:
            if f.get("category") == "syntax":
                reasons.append(f"Introduced new syntax error on line {f.get('line')}: {f.get('message')}")

        # 2. Check for new critical security findings
        old_security_rules = {f.get("rule_id") for f in initial_findings if f.get("category") == "security"}
        for f in new_findings:
            if f.get("category") == "security" and f.get("rule_id") not in old_security_rules:
                reasons.append(f"Introduced new security vulnerability on line {f.get('line')}: {f.get('message')}")

        # 3. Check if target bug rule still exists at same line
        target_still_present = any(f.get("rule_id") == target_rule_id for f in new_findings)
        if target_still_present:
            reasons.append(f"Original bug pattern '{target_rule_id}' was not resolved by the patch.")

        has_regressions = len(reasons) > 0
        return has_regressions, reasons
