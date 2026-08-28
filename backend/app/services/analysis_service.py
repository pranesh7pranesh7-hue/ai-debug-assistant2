"""Analysis Service.
Orchestrates static analysis -> AST bug detection -> severity classification -> AI explanation.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.modules.ai_explanation.explainer import BugExplainer
from app.modules.bug_detection.detector import detect_all_bugs
from app.modules.severity.classifier import SeverityClassifier

logger = logging.getLogger("bugsense.analysis_service")


class AnalysisService:
    """Coordinates end-to-end code analysis pipeline."""

    @staticmethod
    async def run_full_analysis(db: Session, submission_id: int) -> Dict[str, Any]:
        """Execute full static & AI analysis for a submitted code file."""
        submission = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not submission:
            raise NotFoundError("CodeSubmission", submission_id)

        raw_code = submission.raw_code

        # 1. Clear previous bug findings for this submission
        db.query(Bug).filter(Bug.submission_id == submission_id).delete()
        db.commit()

        # 2. Determine Language (respect submission.language if set and valid, fallback to detection)
        from app.services.language_detector import LanguageDetector
        language = None
        if submission.language and submission.language.strip().lower() not in ("auto", "unknown", ""):
            cleaned_lang = submission.language.strip().lower()
            language = LanguageDetector.NORMALIZED_NAMES.get(cleaned_lang, submission.language.strip())

        if not language:
            language = LanguageDetector.detect_language(filename=submission.filename, code=raw_code)
            if language == "Unknown":
                language = "Python"

        # 3. Run static analysis + deep pattern detection
        findings, metrics = await detect_all_bugs(raw_code, language)

        import asyncio

        async def process_bug_item(item: Dict[str, Any]) -> Bug:
            line = item.get("line", 1)
            column = item.get("column", 0)
            tool = item.get("tool", "ast")
            rule_id = item.get("rule_id", "GENERIC")
            category = item.get("category", "logic")
            message = item.get("message", "")

            # Concurrently classify severity and generate explanation
            (sev, score), explanation = await asyncio.gather(
                SeverityClassifier.classify_bug(
                    code_context=raw_code,
                    category=category,
                    rule_id=rule_id,
                    message=message,
                    line=line,
                    use_llm=False,
                    language=language,
                ),
                BugExplainer.explain_bug(
                    raw_code=raw_code,
                    line=line,
                    column=column,
                    tool=tool,
                    rule_id=rule_id,
                    category=category,
                    message=message,
                    language=language,
                )
            )

            return Bug(
                submission_id=submission.id,
                line=line,
                column=column,
                tool=tool,
                rule_id=rule_id,
                category=category,
                message=message,
                severity=sev,
                severity_score=score,
                explanation=explanation,
            )

        if findings:
            created_bugs = await asyncio.gather(*(process_bug_item(f) for f in findings))
            for b in created_bugs:
                db.add(b)
            db.commit()
            for b in created_bugs:
                db.refresh(b)
        else:
            created_bugs = []

        return {
            "submission_id": submission.id,
            "filename": submission.filename,
            "total_bugs": len(created_bugs),
            "complexity_metrics": metrics,
            "bugs": [
                {
                    "id": b.id,
                    "line": b.line,
                    "column": b.column,
                    "tool": b.tool,
                    "rule_id": b.rule_id,
                    "category": b.category,
                    "message": b.message,
                    "severity": b.severity,
                    "severity_score": b.severity_score,
                    "explanation": b.explanation,
                }
                for b in created_bugs
            ],
        }
