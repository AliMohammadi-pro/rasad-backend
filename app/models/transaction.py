from datetime import datetime

from sqlalchemy import (
    String,
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


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assets.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    transaction_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    price: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    total_usdt: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    fee_usdt: Mapped[float] = mapped_column(
        Numeric(30, 10),
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index(
            "ix_transactions_user_time",
            "user_id",
            "created_at"
        ),
    )