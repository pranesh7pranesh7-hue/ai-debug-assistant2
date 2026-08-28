"""Agentic Autonomous Debugging API Routes."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.agentic import (
    AgenticStartRequest,
    AgenticStatusResponse,
    AgenticStepLog,
)
from app.services.agentic_service import AgenticService

router = APIRouter(prefix="/agentic", tags=["Agentic"])


@router.post("/{submission_id}/start", response_model=AgenticStatusResponse)
async def start_agentic_debugging(
    submission_id: int,
    payload: AgenticStartRequest = AgenticStartRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Launch the Plan -> Act -> Observe -> Verify -> Retry agentic debugging loop."""
    result = await AgenticService.start_agentic_loop(
        db=db,
        submission_id=submission_id,
        bug_ids=payload.bug_ids,
        max_retries=payload.max_retries or 3,
        test_code=payload.test_code,
    )

    status_data = AgenticService.get_agentic_status(db, submission_id)
    return AgenticStatusResponse(
        submission_id=status_data["submission_id"],
        status=status_data["status"],
        total_bugs=status_data["total_bugs"],
        fixed_bugs=status_data["fixed_bugs"],
        current_attempt=status_data["current_attempt"],
        max_retries=status_data["max_retries"],
        is_running=status_data["is_running"],
        final_code=status_data.get("final_code"),
        logs=[AgenticStepLog(**item) for item in status_data["logs"]],
    )


@router.get("/{submission_id}/status", response_model=AgenticStatusResponse)
def get_agentic_progress(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll the status, attempts, logs, and verified patches of an ongoing agentic loop."""
    status_data = AgenticService.get_agentic_status(db, submission_id)
    return AgenticStatusResponse(
        submission_id=status_data["submission_id"],
        status=status_data["status"],
        total_bugs=status_data["total_bugs"],
        fixed_bugs=status_data["fixed_bugs"],
        current_attempt=status_data["current_attempt"],
        max_retries=status_data["max_retries"],
        is_running=status_data["is_running"],
        final_code=status_data.get("final_code"),
        logs=[AgenticStepLog(**item) for item in status_data["logs"]],
    )
