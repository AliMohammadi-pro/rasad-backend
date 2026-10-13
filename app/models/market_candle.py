from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    UniqueConstraint,
)

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketCandle(Base):
    """
    Persistent OHLCV candle storage.

    The market updater writes one-minute candles from the stored market
    snapshots. Higher timeframes are aggregated from these 1-minute candles.
    """

    __tablename__ = "market_candles"

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

    interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    open: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    high: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    low: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    close: Mapped[float] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    volume: Mapped[float | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "interval_minutes",
            "recorded_at",
            name="uq_market_candles_asset_interval_time"
        ),
        Index(
            "ix_market_candles_asset_interval_time",
            "asset_id",
            "interval_minutes",
            "recorded_at"
        ),
    )
