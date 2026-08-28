from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class RawCodeUploadRequest(BaseModel):
    filename: str = Field(default="script.py", min_length=1, max_length=255)
    code: str = Field(..., min_length=1)
    language: Optional[str] = None
    project_id: Optional[int] = None


class CodeSubmissionResponse(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int] = None
    filename: str
    language: str = "Python"
    is_project: bool = False
    files_count: int = 1
    source_hash: str
    raw_code: str
    uploaded_at: datetime
    lines_of_code: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("uploaded_at")
    def serialize_uploaded_at(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()




class CodeValidationResult(BaseModel):
    is_valid: bool
    error_message: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
