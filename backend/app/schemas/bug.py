"""Pydantic schemas for Bugs and Static Analysis findings."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class BugResponse(BaseModel):
    id: int
    submission_id: int
    language: str = "Python"
    file_path: Optional[str] = None
    line: int
    column: int
    tool: str
    rule_id: str
    category: str
    message: str
    severity: str
    severity_score: float
    suggestion: Optional[str] = None
    explanation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BugListResponse(BaseModel):
    submission_id: int
    filename: str
    language: str = "Python"
    files_analyzed: int = 1
    total_bugs: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    bugs: List[BugResponse]



class AIExplanationRequest(BaseModel):
    custom_context: Optional[str] = None


class AIExplanationResponse(BaseModel):
    bug_id: int
    explanation: str
    root_cause: str
    potential_runtime_impact: str
