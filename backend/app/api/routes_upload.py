"""Code Upload API Routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.code_submission import CodeSubmission
from app.models.user import User
from app.modules.code_upload.uploader import CodeUploader
from app.schemas.upload import CodeSubmissionResponse, RawCodeUploadRequest

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("", response_model=CodeSubmissionResponse)
def upload_raw_code(
    payload: RawCodeUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit raw Python or multi-language source code for analysis."""
    sub = CodeUploader.process_raw_code(
        db=db,
        user_id=current_user.id,
        raw_code=payload.code,
        filename=payload.filename,
        language=payload.language,
        project_id=payload.project_id,
    )
    return CodeSubmissionResponse(
        id=sub.id,
        user_id=sub.user_id,
        project_id=sub.project_id,
        filename=sub.filename,
        language=sub.language or "Python",
        source_hash=sub.source_hash,
        raw_code=sub.raw_code,
        uploaded_at=sub.uploaded_at,
        lines_of_code=len(sub.raw_code.splitlines()),
    )


@router.post("/file", response_model=List[CodeSubmissionResponse])
async def upload_code_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    project_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a supported source file or .zip project archive."""
    file_bytes = await file.read()
    subs = CodeUploader.process_file_upload(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "code.py",
        file_bytes=file_bytes,
        language=language,
        project_id=project_id,
    )
    return [
        CodeSubmissionResponse(
            id=s.id,
            user_id=s.user_id,
            project_id=s.project_id,
            filename=s.filename,
            language=s.language or "Python",
            source_hash=s.source_hash,
            raw_code=s.raw_code,
            uploaded_at=s.uploaded_at,
            lines_of_code=len(s.raw_code.splitlines()),
        )
        for s in subs
    ]


@router.get("/history", response_model=List[CodeSubmissionResponse])
def get_user_submissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent code submissions for the logged-in user."""
    subs = (
        db.query(CodeSubmission)
        .filter(CodeSubmission.user_id == current_user.id)
        .order_by(CodeSubmission.uploaded_at.desc())
        .all()
    )
    return [
        CodeSubmissionResponse(
            id=s.id,
            user_id=s.user_id,
            project_id=s.project_id,
            filename=s.filename,
            language=s.language or "Python",
            source_hash=s.source_hash,
            raw_code=s.raw_code,
            uploaded_at=s.uploaded_at,
            lines_of_code=len(s.raw_code.splitlines()),
        )
        for s in subs
    ]
