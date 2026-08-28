"""Report Service.
Manages report retrieval, generation, and AI developer assistant chat.
"""
import json
import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.models.report import Report
from app.modules.llm.llm_client import get_llm_client
from app.modules.report_generation.report_builder import ReportBuilder


class ReportService:
    """Service for reports and chat assistant."""

    @staticmethod
    def get_or_build_report(db: Session, submission_id: int) -> Dict[str, Any]:
        """Fetch existing report or generate a new one."""
        db_report = db.query(Report).filter(Report.submission_id == submission_id).first()
        if not db_report:
            db_report = ReportBuilder.generate_report(db, submission_id)

        summary_data = json.loads(db_report.summary_json)
        return {
            "id": db_report.id,
            "submission_id": db_report.submission_id,
            "filename": summary_data.get("filename", "code.py"),
            "generated_at": db_report.generated_at,
            "total_bugs": summary_data.get("total_bugs", 0),
            "severity_breakdown": summary_data.get("severity_breakdown", {}),
            "category_breakdown": summary_data.get("category_breakdown", {}),
            "auto_fixed_count": summary_data.get("auto_fixed_count", 0),
            "complexity_score": summary_data.get("complexity_score", 1.0),
            "maintainability_index": 85.0,
            "summary_json": summary_data,
            "pdf_available": bool(db_report.pdf_path and os.path.exists(db_report.pdf_path)),
        }

    @staticmethod
    def get_pdf_path(db: Session, submission_id: int) -> str:
        """Get absolute path to downloadable PDF report."""
        db_report = db.query(Report).filter(Report.submission_id == submission_id).first()
        if not db_report:
            db_report = ReportBuilder.generate_report(db, submission_id)

        if not db_report.pdf_path or not os.path.exists(db_report.pdf_path):
            db_report = ReportBuilder.generate_report(db, submission_id)

        return db_report.pdf_path

    @staticmethod
    async def chat_with_assistant(
        db: Session,
        submission_id: int,
        user_message: str,
        bug_id: Optional[int] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Intelligent developer assistant panel on report page."""
        sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not sub:
            raise NotFoundError("CodeSubmission", submission_id)

        bug_context_str = ""
        if bug_id:
            bug = db.query(Bug).filter(Bug.id == bug_id).first()
            if bug:
                bug_context_str = (
                    f"Selected Bug Finding:\n"
                    f"- Line {bug.line} ({bug.rule_id}): {bug.message}\n"
                    f"- Category: {bug.category} | Severity: {bug.severity}\n"
                    f"- Explanation: {bug.explanation}\n"
                )

        history_context = ""
        if chat_history:
            for item in chat_history[-4:]:
                history_context += f"{item.get('role', 'user').capitalize()}: {item.get('content', '')}\n"

        from app.services.language_detector import LanguageDetector
        language = LanguageDetector.detect_language(filename=sub.filename, code=sub.raw_code)
        lang_tag = language.lower().replace("+", "p").replace("#", "sharp")

        prompt = (
            f"You are BugSense AI Assistant, an expert {language} debugging pair programmer.\n\n"
            f"Context Code File: {sub.filename} (Language: {language})\n"
            f"```{lang_tag}\n{sub.raw_code[:3000]}\n```\n\n"
            f"{bug_context_str}\n"
            f"Conversation History:\n{history_context}\n\n"
            f"Developer Question: {user_message}\n\n"
            f"Provide an insightful, helpful, concise answer with code examples if applicable."
        )

        llm = get_llm_client()
        reply_text = await llm.generate_text(prompt)

        return {
            "reply": reply_text,
            "code_suggestion": None,
        }
