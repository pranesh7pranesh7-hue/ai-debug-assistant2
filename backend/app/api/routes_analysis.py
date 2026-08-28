"""Static & AI Analysis API Routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.code_submission import CodeSubmission
from app.models.user import User
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/{submission_id}/run")
async def run_analysis(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger complete static analysis + AST bug detection + severity scoring + AI explanation pipeline."""
    result = await AnalysisService.run_full_analysis(db, submission_id)
    return result


@router.get("/{submission_id}/status")
def get_analysis_status(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check status and metadata for a submission's analysis."""
    sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
    if not sub:
        return {"status": "not_found", "submission_id": submission_id}

    has_bugs = len(sub.bugs) > 0
    return {
        "submission_id": sub.id,
        "filename": sub.filename,
        "status": "completed" if has_bugs else "ready_to_analyze",
        "total_bugs_detected": len(sub.bugs),
    }
