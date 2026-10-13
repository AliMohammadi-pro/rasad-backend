from datetime import datetime
from decimal import Decimal
from app.utils.time import utc_now

from sqlalchemy import (
    DateTime,
    Numeric,
    ForeignKey,
    Index
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database import Base


class Deposit(Base):
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    amount_usdt: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=lambda: utc_now().replace(tzinfo=None),
    nullable=False,
    index=True
)
    __table_args__ = (
        Index(
            "ix_deposits_user_time",
            "user_id",
            "created_at"
        ),
    )