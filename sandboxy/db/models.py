"""SQLAlchemy models for Sandboxy."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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


# =============================================================================
# Arena Models - Multi-model comparison and testing
# =============================================================================


class JudgeTemplate(Base):
    """A reusable judge template for evaluating responses.

    Judges are prompts too! This allows users to create and share
    evaluation criteria that can be reused across challenges.
    """

    __tablename__ = "judge_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Judge type: llm, contains, regex, exact, length, consensus
    judge_type: Mapped[str] = mapped_column(String(50), nullable=False, default="llm")

    # For LLM judges: the evaluation prompt template
    # Supports {{response}}, {{prompt}}, {{model_id}} variables
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # For non-LLM judges
    pattern: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    min_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Consensus judge voters
    voters: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Scoring
    pass_threshold: Mapped[float] = mapped_column(Float, default=0.5)

    # Ownership
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ArenaPrompt(Base):
    """A prompt template for arena runs (challenges)."""

    __tablename__ = "arena_prompts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Judge config: either inline or reference to template
    judge_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    judge_template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("judge_templates.id"), nullable=True
    )

    variables: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # For hosted: who created it
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    runs: Mapped[list["ArenaRun"]] = relationship(back_populates="prompt")
    judge_template: Mapped["JudgeTemplate | None"] = relationship()


class ArenaRun(Base):
    """A run of a prompt against multiple models."""

    __tablename__ = "arena_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    prompt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("arena_prompts.id"), nullable=True, index=True
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    models: Mapped[list] = mapped_column(JSON, nullable=False)

    # Timing and cost
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # For hosted: who ran it
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    prompt: Mapped["ArenaPrompt | None"] = relationship(back_populates="runs")
    results: Mapped[list["ArenaResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    video: Mapped["ArenaVideo | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )


class ArenaResult(Base):
    """Result from a single model in an arena run."""

    __tablename__ = "arena_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("arena_runs.id"), nullable=False, index=True
    )
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Response data
    response: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Judgment data
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    judgment_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    run: Mapped["ArenaRun"] = relationship(back_populates="results")


class ArenaVideo(Base):
    """Generated video for an arena run."""

    __tablename__ = "arena_videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("arena_runs.id"), nullable=False, unique=True
    )

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    template: Mapped[str] = mapped_column(String(100), nullable=False, default="showdown")

    # Storage
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cdn_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadata
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped["ArenaRun"] = relationship(back_populates="video")
