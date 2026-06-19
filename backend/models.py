"""SQLAlchemy models: Project and Interview.

A Project groups all the stakeholder interviews for one engagement. Each
Interview is a single stakeholder's conversation plus the structured summary
the agent produces at the end.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    # Short url-safe code used in the shareable link /p/{public_id}.
    public_id = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    client_name = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=_now)

    interviews = relationship(
        "Interview", back_populates="project", cascade="all, delete-orphan"
    )


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    stakeholder_name = Column(String(200), nullable=False)
    stakeholder_role = Column(String(200), nullable=False)

    status = Column(String(20), default="in_progress")  # in_progress | completed

    # Full Anthropic-format message list (list of {role, content}).
    transcript = Column(JSON, default=list)
    # The structured summary produced by the save_summary tool.
    summary_json = Column(JSON, nullable=True)
    # Number of completed user<->assistant exchanges, used to pace wrap-up.
    turn_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=_now)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="interviews")
