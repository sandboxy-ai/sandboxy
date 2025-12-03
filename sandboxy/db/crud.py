"""CRUD operations for database models."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sandboxy.db.models import Evaluation, Module, Session, SessionEvent

# --- Module CRUD ---


async def get_modules(db: AsyncSession) -> list[Module]:
    """Get all modules."""
    result = await db.execute(select(Module).order_by(Module.created_at.desc()))
    return list(result.scalars().all())


async def get_module_by_slug(db: AsyncSession, slug: str) -> Module | None:
    """Get a module by its slug."""
    result = await db.execute(select(Module).where(Module.slug == slug))
    return result.scalar_one_or_none()


async def get_module_by_id(db: AsyncSession, module_id: str) -> Module | None:
    """Get a module by its ID."""
    result = await db.execute(select(Module).where(Module.id == module_id))
    return result.scalar_one_or_none()


async def create_module(
    db: AsyncSession,
    slug: str,
    name: str,
    yaml_content: str,
    description: str | None = None,
    icon: str | None = None,
    category: str | None = None,
) -> Module:
    """Create a new module."""
    module = Module(
        slug=slug,
        name=name,
        yaml_content=yaml_content,
        description=description,
        icon=icon,
        category=category,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


async def update_module(
    db: AsyncSession,
    module: Module,
    name: str | None = None,
    yaml_content: str | None = None,
    description: str | None = None,
    icon: str | None = None,
    category: str | None = None,
) -> Module:
    """Update an existing module."""
    if name is not None:
        module.name = name
    if yaml_content is not None:
        module.yaml_content = yaml_content
    if description is not None:
        module.description = description
    if icon is not None:
        module.icon = icon
    if category is not None:
        module.category = category

    await db.commit()
    await db.refresh(module)
    return module


async def delete_module(db: AsyncSession, module: Module) -> None:
    """Delete a module."""
    await db.delete(module)
    await db.commit()


# --- Session CRUD ---


async def get_sessions(
    db: AsyncSession,
    module_id: str | None = None,
    limit: int = 50,
) -> list[Session]:
    """Get sessions, optionally filtered by module."""
    query = select(Session).order_by(Session.created_at.desc()).limit(limit)
    if module_id:
        query = query.where(Session.module_id == module_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_session_by_id(
    db: AsyncSession,
    session_id: str,
    include_events: bool = False,
) -> Session | None:
    """Get a session by ID."""
    query = select(Session).where(Session.id == session_id)
    if include_events:
        query = query.options(selectinload(Session.events), selectinload(Session.evaluation))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    module_id: str,
    agent_id: str,
    variables: dict | None = None,
) -> Session:
    """Create a new session."""
    session = Session(
        module_id=module_id,
        agent_id=agent_id,
        variables=variables,
        state="idle",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def update_session_state(
    db: AsyncSession,
    session: Session,
    state: str,
) -> Session:
    """Update session state."""
    session.state = state
    if state == "running" and session.started_at is None:
        session.started_at = datetime.utcnow()
    elif state in ("completed", "error"):
        session.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session: Session) -> None:
    """Delete a session and its events."""
    await db.delete(session)
    await db.commit()


# --- SessionEvent CRUD ---


async def add_session_event(
    db: AsyncSession,
    session_id: str,
    sequence: int,
    event_type: str,
    payload: dict,
) -> SessionEvent:
    """Add an event to a session."""
    event = SessionEvent(
        session_id=session_id,
        sequence=sequence,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_session_events(db: AsyncSession, session_id: str) -> list[SessionEvent]:
    """Get all events for a session."""
    result = await db.execute(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.sequence)
    )
    return list(result.scalars().all())


# --- Evaluation CRUD ---


async def create_evaluation(
    db: AsyncSession,
    session_id: str,
    score: float | None = None,
    checks: dict | None = None,
) -> Evaluation:
    """Create an evaluation for a session."""
    evaluation = Evaluation(
        session_id=session_id,
        score=score,
        checks=checks,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def get_evaluation_by_session(db: AsyncSession, session_id: str) -> Evaluation | None:
    """Get evaluation for a session."""
    result = await db.execute(select(Evaluation).where(Evaluation.session_id == session_id))
    return result.scalar_one_or_none()
