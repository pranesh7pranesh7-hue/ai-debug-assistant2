"""SQLAlchemy Report Model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_json = Column(Text, nullable=False)  # Full JSON report dump
    pdf_path = Column(String(500), nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    submission = relationship("CodeSubmission", back_populates="reports")
