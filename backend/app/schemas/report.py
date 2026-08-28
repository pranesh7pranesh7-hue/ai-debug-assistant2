"""Pydantic schemas for Reports and AI Chat Assistant."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ReportSummaryResponse(BaseModel):
    id: int
    submission_id: int
    filename: str
    generated_at: datetime
    total_bugs: int
    severity_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    auto_fixed_count: int
    complexity_score: Optional[float] = None
    maintainability_index: Optional[float] = None
    summary_json: Dict[str, Any]
    pdf_available: bool

    model_config = ConfigDict(from_attributes=True)



class AIChatRequest(BaseModel):
    submission_id: int
    bug_id: Optional[int] = None
    message: str
    chat_history: Optional[List[Dict[str, str]]] = None


class AIChatResponse(BaseModel):
    reply: str
    code_suggestion: Optional[str] = None
