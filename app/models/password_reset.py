from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String
)

from app.database import Base


class PasswordReset(Base):

    __tablename__ = "password_resets"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )

    expires_at = Column(
        DateTime,
        nullable=False
    )

    used_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )