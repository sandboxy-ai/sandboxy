"""SQLAlchemy models for Sandboxy."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Module(Base):
    """A scenario module that can be run."""

    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(back_populates="module")


class Session(Base):
    """An interactive session running a module."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("modules.id"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    variables: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    module: Mapped["Module"] = relationship(back_populates="sessions")
    events: Mapped[list["SessionEvent"]] = relationship(
        back_populates="session", order_by="SessionEvent.sequence"
    )
    evaluation: Mapped["Evaluation | None"] = relationship(back_populates="session", uselist=False)


class SessionEvent(Base):
    """An event that occurred during a session."""

    __tablename__ = "session_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="events")


class Evaluation(Base):
    """Evaluation results for a completed session."""

    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, unique=True, index=True
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    checks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="evaluation")
