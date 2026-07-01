"""
User Session model for tracking trader sessions per user.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSession(Base):
    """User Session model for storing session metadata and ownership tracking."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        unique=True,
    )
    label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Composite index for faster queries
    __table_args__ = (
        Index("ix_user_sessions_user_id_is_active", "user_id", "is_active"),
        Index("ix_user_sessions_user_id_session_id", "user_id", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} session_id={self.session_id}>"
