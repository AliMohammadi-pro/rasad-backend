from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Numeric,
    ForeignKey
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    balance_usdt: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        default=Decimal("0"),
        nullable=False
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