"""Pydantic schemas for User Authentication and Profiles."""
import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not re.match(EMAIL_REGEX, cleaned):
            raise ValueError("Invalid email address format.")
        return cleaned


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not re.match(EMAIL_REGEX, cleaned):
            raise ValueError("Invalid email address format.")
        return cleaned


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class UserProfileResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


