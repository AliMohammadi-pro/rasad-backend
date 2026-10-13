from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    Numeric,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EconomicIndicator(Base):
    __tablename__ = "economic_indicators"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    indicator: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    date: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    value: Mapped[float | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    unit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    source: Mapped[str] = mapped_column(
        String(100),
        default="Alpha Vantage",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "indicator",
            "date",
            name="uq_economic_indicator_date"
        ),
        Index(
            "ix_economic_indicator_indicator_date",
            "indicator",
            "date"
        ),
    )