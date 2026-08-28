"""Verification Service."""
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.modules.fix_verification.verifier import FixVerifier


class VerificationService:
    """Coordinates manual and automated patch verification checks."""

    @staticmethod
    async def verify_submission_patch(
        db: Session,
        submission_id: int,
        bug_id: int,
        patched_code: str,
    ) -> Dict[str, Any]:
        """Runs full verification suite on a candidate patched code."""
        sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not sub:
            raise NotFoundError("CodeSubmission", submission_id)

        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise NotFoundError("Bug", bug_id)

        target_bug_dict = {
            "id": bug.id,
            "line": bug.line,
            "column": bug.column,
            "tool": bug.tool,
            "rule_id": bug.rule_id,
            "category": bug.category,
            "message": bug.message,
        }

        verdict = await FixVerifier.verify_patch(
            original_code=sub.raw_code,
            patched_code=patched_code,
            target_bug=target_bug_dict,
        )

        return verdict
