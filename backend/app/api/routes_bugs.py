"""Bug Details & AI Explanation API Routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.dependencies import get_current_user
from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.models.user import User
from app.schemas.bug import (
    AIExplanationRequest,
    AIExplanationResponse,
    BugListResponse,
    BugResponse,
)
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/bugs", tags=["Bugs"])


@router.get("/{submission_id}", response_model=BugListResponse)
def get_submission_bugs(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all detected bugs and AI diagnostics for a submission."""
    sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
    if not sub:
        raise NotFoundError("CodeSubmission", submission_id)

    bugs = db.query(Bug).filter(Bug.submission_id == submission_id).order_by(Bug.severity_score.desc()).all()

    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for b in bugs:
        counts[b.severity] = counts.get(b.severity, 0) + 1

    return BugListResponse(
        submission_id=sub.id,
        filename=sub.filename,
        total_bugs=len(bugs),
        critical_count=counts.get("Critical", 0),
        high_count=counts.get("High", 0),
        medium_count=counts.get("Medium", 0),
        low_count=counts.get("Low", 0),
        info_count=counts.get("Info", 0),
        bugs=[
            BugResponse(
                id=b.id,
                submission_id=b.submission_id,
                line=b.line,
                column=b.column,
                tool=b.tool,
                rule_id=b.rule_id,
                category=b.category,
                message=b.message,
                severity=b.severity,
                severity_score=b.severity_score,
                explanation=b.explanation,
                created_at=b.created_at,
            )
            for b in bugs
        ],
    )


@router.post("/{bug_id}/explain", response_model=BugResponse)
async def generate_bug_explanation(
    bug_id: int,
    payload: AIExplanationRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate or retrieve deep AI root-cause explanation for a bug."""
    bug = await ExplanationService.get_or_generate_explanation(db, bug_id)
    return BugResponse(
        id=bug.id,
        submission_id=bug.submission_id,
        line=bug.line,
        column=bug.column,
        tool=bug.tool,
        rule_id=bug.rule_id,
        category=bug.category,
        message=bug.message,
        severity=bug.severity,
        severity_score=bug.severity_score,
        explanation=bug.explanation,
        created_at=bug.created_at,
    )
