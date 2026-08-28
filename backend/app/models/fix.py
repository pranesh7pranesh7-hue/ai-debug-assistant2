"""SQLAlchemy Fix Model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Fix(Base):
    __tablename__ = "fixes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bug_id = Column(Integer, ForeignKey("bugs.id", ondelete="CASCADE"), nullable=False, index=True)
    diff_text = Column(Text, nullable=False)
    patched_code = Column(Text, nullable=True)
    rationale = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="proposed")  # proposed, applied, verified, rejected, failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    bug = relationship("Bug", back_populates="fixes")
