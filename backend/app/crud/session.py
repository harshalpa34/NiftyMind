"""
CRUD operations for user sessions.
"""
import logging
from uuid import UUID
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_session import UserSession

logger = logging.getLogger(__name__)


async def create_user_session(
    db: AsyncSession,
    user_id: UUID,
    session_id: str,
    label: Optional[str] = None,
) -> UserSession:
    """
    Create a new user session record.

    Args:
        db: AsyncSession for database operations
        user_id: User UUID
        session_id: Session identifier (from LangGraph)
        label: Optional label for the session

    Returns:
        Created UserSession model instance

    Raises:
        Exception: If database operation fails
    """
    user_session = UserSession(
        user_id=user_id,
        session_id=session_id,
        label=label,
        is_active=True,
    )
    db.add(user_session)
    await db.flush()
    await db.refresh(user_session)

    logger.info(
        "User session created",
        extra={
            "user_id": str(user_id),
            "session_id": session_id,
            "label": label,
        },
    )

    return user_session


async def get_user_sessions(
    db: AsyncSession,
    user_id: UUID,
) -> list[UserSession]:
    """
    Get all active sessions for a user.

    Args:
        db: AsyncSession for database operations
        user_id: User UUID

    Returns:
        List of UserSession records for the user, ordered by created_at DESC

    Raises:
        Exception: If database operation fails
    """
    query = (
        select(UserSession)
        .where(
            (UserSession.user_id == user_id)
            & (UserSession.is_active == True)
        )
        .order_by(UserSession.created_at.desc())
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    logger.debug(
        "Retrieved user sessions",
        extra={"user_id": str(user_id), "count": len(sessions)},
    )

    return sessions


async def verify_session_ownership(
    db: AsyncSession,
    user_id: UUID,
    session_id: str,
) -> bool:
    """
    Verify that a user owns a session.

    Args:
        db: AsyncSession for database operations
        user_id: User UUID
        session_id: Session identifier

    Returns:
        True if user owns the session, False otherwise

    Raises:
        Exception: If database operation fails
    """
    query = select(UserSession).where(
        (UserSession.user_id == user_id) & (UserSession.session_id == session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    logger.debug(
        "Session ownership verified",
        extra={
            "user_id": str(user_id),
            "session_id": session_id,
            "owned": session is not None,
        },
    )

    return session is not None
