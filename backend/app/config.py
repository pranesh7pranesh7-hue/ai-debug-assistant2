"""Application Configuration Settings via Pydantic Settings."""
from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """BugSense AI Environment Settings."""

    APP_NAME: str = "BugSense AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-in-production-super-secret-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Database: Default PostgreSQL, fallback to SQLite for local standalone setup
    DATABASE_URL: str = "sqlite:///./bugsense.db"

    # LLM Settings
    LLM_PROVIDER: str = "anthropic"  # anthropic, openai, gemini, ollama, mock
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 2048

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Upload & Sandbox Constraints
    MAX_UPLOAD_SIZE_MB: int = 2
    SANDBOX_TIMEOUT_SECONDS: int = 5
    MAX_AGENTIC_RETRIES: int = 3

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton instance of application settings."""
    return Settings()
