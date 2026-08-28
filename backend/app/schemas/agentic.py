"""Pydantic schemas for Agentic Debugging Loop runs and status."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AgenticStartRequest(BaseModel):
    bug_ids: Optional[List[int]] = None
    max_retries: Optional[int] = 3
    test_code: Optional[str] = None  # Optional test suite code to execute in sandbox


class AgenticStepLog(BaseModel):
    attempt_number: int
    action_taken: str
    diff_applied: Optional[str] = None
    outcome: str
    verified: bool
    created_at: datetime


class AgenticStatusResponse(BaseModel):
    submission_id: int
    status: str  # in_progress, completed, failed, verified
    total_bugs: int
    fixed_bugs: int
    current_attempt: int
    max_retries: int
    is_running: bool
    logs: List[AgenticStepLog]
    final_code: Optional[str] = None
