"""Explanation Service."""
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError
from app.models.bug import Bug
from app.modules.ai_explanation.explainer import BugExplainer


class ExplanationService:
    """Generates on-demand detailed explanations for bugs."""

    @staticmethod
    async def get_or_generate_explanation(db: Session, bug_id: int) -> Bug:
        """Fetch or regenerate explanation for specific bug."""
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise NotFoundError("Bug", bug_id)

        if not bug.explanation:
            raw_code = bug.submission.raw_code
            explanation = await BugExplainer.explain_bug(
                raw_code=raw_code,
                line=bug.line,
                column=bug.column,
                tool=bug.tool,
                rule_id=bug.rule_id,
                category=bug.category,
                message=bug.message,
                language=bug.language or "Python",
            )
            bug.explanation = explanation
            db.commit()
            db.refresh(bug)

        return bug
