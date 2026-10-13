from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioSnapshot(Base):

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    balance_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    crypto_value_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    total_wallet_value_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    total_cost_basis_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    realized_cost_basis_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    realized_pnl_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    unrealized_pnl_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    total_pnl_usdt: Mapped[Numeric] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    pnl_percentage: Mapped[Numeric] = mapped_column(
        Numeric(20, 10),
        nullable=False
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index(
            "ix_portfolio_snapshots_user_recorded",
            "user_id",
            "recorded_at"
        ),
    )