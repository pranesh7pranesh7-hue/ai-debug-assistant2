"""SQLAlchemy Bug Model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.database import Base


class Bug(Base):
    __tablename__ = "bugs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(50), nullable=False, default="Python")
    file_path = Column(String(255), nullable=True)
    line = Column(Integer, nullable=False, default=1)
    column = Column(Integer, nullable=False, default=0)
    tool = Column(String(50), nullable=False)  # ast, pylint, gcc, clang, javac, eslint, etc.
    rule_id = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # Critical, High, Medium, Low, Info
    severity_score = Column(Float, nullable=False, default=0.0)  # 0 - 100
    suggestion = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)  # AI-generated root-cause explanation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    submission = relationship("CodeSubmission", back_populates="bugs")
    fixes = relationship("Fix", back_populates="bug", cascade="all, delete-orphan")
    agentic_runs = relationship("AgenticRun", back_populates="bug", cascade="all, delete-orphan")

