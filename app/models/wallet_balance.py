from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Index
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database import Base


class WalletBalance(Base):
    __tablename__ = "wallet_balances"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(30, 18),
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

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "asset_id",
            name="uq_wallet_balance_user_asset"
        ),
        Index(
            "ix_wallet_balances_user_asset",
            "user_id",
            "asset_id"
        ),
    )