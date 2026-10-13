from datetime import datetime

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


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
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

    price: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    change_24h: Mapped[float] = mapped_column(
        Numeric(12, 4),
        default=0,
        nullable=False
    )

    volume_24h: Mapped[float | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    market_cap: Mapped[float | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index(
            "ix_market_prices_asset_time",
            "asset_id",
            "recorded_at"
        ),
    )
