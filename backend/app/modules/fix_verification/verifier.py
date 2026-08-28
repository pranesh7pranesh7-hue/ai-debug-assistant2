"""Fix Verification Module.
Coordinates static analysis re-execution, regression verification, and sandbox evaluation.
"""
from typing import Any, Dict, Optional
from app.modules.bug_detection.detector import detect_all_bugs
from app.modules.fix_verification.regression_checker import RegressionChecker


class FixVerifier:
    """Evaluates patches against static analyzers and regression metrics."""

    @staticmethod
    async def verify_patch(
        original_code: str,
        patched_code: str,
        target_bug: Dict[str, Any],
        sandbox_success: bool = True,
    ) -> Dict[str, Any]:
        """Comprehensive multi-factor patch verification."""
        # 1. Run static analysis on patched code
        new_findings, _ = await detect_all_bugs(patched_code)

        target_rule_id = target_bug.get("rule_id", "")
        target_line = target_bug.get("line", 1)

        # Check if original bug signature still exists
        original_still_exists = False
        for f in new_findings:
            if f.get("rule_id") == target_rule_id and abs(f.get("line", 1) - target_line) <= 2:
                original_still_exists = True
                break

        # Check for regressions
        has_regressions, regression_notes = RegressionChecker.check_regressions(
            initial_findings=[target_bug],
            new_findings=new_findings,
            target_rule_id=target_rule_id,
        )

        passed = (not original_still_exists) and (not has_regressions) and sandbox_success

        if passed:
            summary = f"Fix verified successfully. Bug '{target_rule_id}' eliminated with 0 regressions."
        else:
            reasons = []
            if original_still_exists:
                reasons.append(f"Target bug '{target_rule_id}' still detected in patched source.")
            if not sandbox_success:
                reasons.append("Sandbox execution produced runtime failure.")
            reasons.extend(regression_notes)
            summary = "Verification failed: " + "; ".join(reasons)

        return {
            "passed": passed,
            "summary": summary,
            "original_bug_cleared": not original_still_exists,
            "sandbox_passed": sandbox_success,
            "new_findings_count": len(new_findings),
            "evidence": {
                "regression_notes": regression_notes,
                "remaining_findings": new_findings[:5],
            },
        }
