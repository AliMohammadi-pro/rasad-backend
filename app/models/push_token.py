from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PushToken(Base):
    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True
    )

    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="android"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User",
        backref="push_tokens"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "token",
            name="uq_user_push_token"
        ),
    )