"""Severity Classification Module.
Hybrid Classifier: rule-based baseline mapping + LLM context-aware scoring.
Outputs: Critical, High, Medium, Low, Info with a numeric score 0-100.
"""
import logging
from typing import Dict, Any, Tuple

from app.modules.llm.llm_client import get_llm_client
from app.modules.severity.severity_rules import get_rule_baseline_severity
from app.utils.constants import SEVERITY_LEVELS

logger = logging.getLogger("bugsense.severity")


class SeverityClassifier:
    """Hybrid rule + AI severity classifier."""

    @staticmethod
    async def classify_bug(
        code_context: str,
        category: str,
        rule_id: str,
        message: str,
        line: int,
        use_llm: bool = False,
        language: str = "Python",
    ) -> Tuple[str, float]:
        """Determine final severity level and score."""
        base_severity, base_score = get_rule_baseline_severity(category, rule_id, message)

        if not use_llm:
            return base_severity, base_score

        # LLM Context-Aware Refinement
        try:
            llm = get_llm_client()
            lang_tag = language.lower().replace("+", "p").replace("#", "sharp")
            prompt = (
                f"You are a code security and reliability auditor. Score the severity of this {language} bug finding in context:\n\n"
                f"File Context (Language: {language}, around line {line}):\n```{lang_tag}\n{code_context}\n```\n\n"
                f"Bug Metadata:\n"
                f"- Category: {category}\n"
                f"- Rule ID: {rule_id}\n"
                f"- Finding Message: {message}\n"
                f"- Baseline Rule Severity: {base_severity} ({base_score}/100)\n\n"
                f"Classify the final severity as one of: Critical, High, Medium, Low, Info.\n"
                f"Provide a numeric severity score between 0.0 and 100.0.\n"
                f"Respond with a JSON object: {{\"severity\": \"...\", \"severity_score\": 0.0, \"rationale\": \"...\"}}"
            )

            res = await llm.generate_json(prompt)
            sev = res.get("severity", base_severity)
            score = float(res.get("severity_score", base_score))

            if sev in SEVERITY_LEVELS and 0.0 <= score <= 100.0:
                return sev, round(score, 1)

        except Exception as e:
            logger.debug("LLM severity refinement fallback: %s", str(e))

        return base_severity, base_score
