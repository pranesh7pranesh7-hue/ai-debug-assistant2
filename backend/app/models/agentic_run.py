"""SQLAlchemy AgenticRun Model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class AgenticRun(Base):
    __tablename__ = "agentic_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    bug_id = Column(Integer, ForeignKey("bugs.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    action_taken = Column(String(50), nullable=False)  # plan, act, observe, verify, retry
    diff_applied = Column(Text, nullable=True)
    outcome = Column(Text, nullable=False)  # Execution result, logs or verification feedback
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    submission = relationship("CodeSubmission", back_populates="agentic_runs")
    bug = relationship("Bug", back_populates="agentic_runs")
