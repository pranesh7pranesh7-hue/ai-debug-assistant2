"""Fix Recommendations & Unified Diff API Routes."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.fix import Fix
from app.models.user import User
from app.schemas.fix import FixGenerateRequest, FixResponse
from app.services.fix_service import FixService

router = APIRouter(prefix="/fixes", tags=["Fixes"])


@router.post("/{bug_id}/generate", response_model=FixResponse)
async def generate_fix(
    bug_id: int,
    payload: FixGenerateRequest = FixGenerateRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a concrete patch (unified diff) and rationale for a bug."""
    fix = await FixService.generate_fix_for_bug(
        db=db,
        bug_id=bug_id,
        custom_instruction=payload.custom_instruction or "",
    )
    return FixResponse(
        id=fix.id,
        bug_id=fix.bug_id,
        diff_text=fix.diff_text,
        patched_code=fix.patched_code,
        rationale=fix.rationale,
        status=fix.status,
        created_at=fix.created_at,
    )


@router.get("/{bug_id}", response_model=List[FixResponse])
def get_fixes(
    bug_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all candidate fixes generated for a bug."""
    fixes = FixService.get_fixes_for_bug(db, bug_id)
    return [
        FixResponse(
            id=f.id,
            bug_id=f.bug_id,
            diff_text=f.diff_text,
            patched_code=f.patched_code,
            rationale=f.rationale,
            status=f.status,
            created_at=f.created_at,
        )
        for f in fixes
    ]
