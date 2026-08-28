"""SQLAlchemy CodeSubmission Model."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    language = Column(String(50), nullable=False, default="Python")
    is_project = Column(Boolean, default=False, nullable=False)
    files_count = Column(Integer, default=1, nullable=False)
    source_hash = Column(String(64), nullable=False, index=True)
    raw_code = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="submissions")
    project = relationship("Project", back_populates="submissions")
    bugs = relationship("Bug", back_populates="submission", cascade="all, delete-orphan")
    agentic_runs = relationship("AgenticRun", back_populates="submission", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="submission", cascade="all, delete-orphan")

