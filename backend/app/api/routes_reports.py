"""Audit Reports and AI Assistant Chat API Routes."""
import os
from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.report import AIChatRequest, AIChatResponse, ReportSummaryResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{submission_id}", response_model=ReportSummaryResponse)
def get_report(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full structured JSON audit report."""
    report_data = ReportService.get_or_build_report(db, submission_id)
    return ReportSummaryResponse(**report_data)


@router.get("/{submission_id}/pdf")
def download_pdf_report(
    submission_id: int,
    db: Session = Depends(get_db),
):
    """Download exportable PDF / printable audit report."""
    file_path = ReportService.get_pdf_path(db, submission_id)
    if not os.path.exists(file_path):
        raise NotFoundError("ReportFile", submission_id)

    # Read content to check format
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read(500)

    # If the file is HTML (printable report format), serve with text/html for immediate browser viewing & printing
    if content.strip().startswith("<!DOCTYPE") or "<html" in content or file_path.endswith(".html"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return HTMLResponse(content=f.read())

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"BugSense_Report_Sub_{submission_id}.pdf",
    )


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_assistant(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Interactive developer pair programmer chat panel on report page."""
    result = await ReportService.chat_with_assistant(
        db=db,
        submission_id=payload.submission_id,
        user_message=payload.message,
        bug_id=payload.bug_id,
        chat_history=payload.chat_history,
    )
    return AIChatResponse(**result)
