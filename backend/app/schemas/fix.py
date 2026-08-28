"""Pydantic schemas for Fix Recommendations and Patches."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class FixGenerateRequest(BaseModel):
    temperature: Optional[float] = None
    custom_instruction: Optional[str] = None


class FixResponse(BaseModel):
    id: int
    bug_id: int
    diff_text: str
    patched_code: Optional[str] = None
    rationale: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ApplyFixRequest(BaseModel):
    fix_id: int


class CandidateFixesResponse(BaseModel):
    bug_id: int
    fixes: List[FixResponse]
