"""Fix Service.
Orchestrates AI fix synthesis, candidate diff generation, and fix application.
"""
from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bug import Bug
from app.models.fix import Fix
from app.modules.fix_recommendation.recommender import FixRecommender


class FixService:
    """Manages generation, storage, and retrieval of code fixes."""

    @staticmethod
    async def generate_fix_for_bug(
        db: Session,
        bug_id: int,
        custom_instruction: str = "",
    ) -> Fix:
        """Generate AI patch and persist candidate fix record."""
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise NotFoundError("Bug", bug_id)

        raw_code = bug.submission.raw_code
        language = bug.submission.language or "Python"
        filename = bug.submission.filename or "code.py"

        fix_dict = await FixRecommender.generate_fix(
            raw_code=raw_code,
            line=bug.line,
            tool=bug.tool,
            rule_id=bug.rule_id,
            message=bug.message,
            category=bug.category,
            explanation=bug.explanation or "",
            custom_instruction=custom_instruction,
            language=language,
            filename=filename,
        )

        db_fix = Fix(
            bug_id=bug.id,
            diff_text=fix_dict.get("diff_text", ""),
            patched_code=fix_dict.get("patched_code", ""),
            rationale=fix_dict.get("rationale", "AI proposed patch"),
            status=fix_dict.get("status", "proposed"),
        )
        db.add(db_fix)
        db.commit()
        db.refresh(db_fix)
        return db_fix

    @staticmethod
    def get_fixes_for_bug(db: Session, bug_id: int) -> List[Fix]:
        """Fetch all generated fixes for a bug."""
        return db.query(Fix).filter(Fix.bug_id == bug_id).all()
