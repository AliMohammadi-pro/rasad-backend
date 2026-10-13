from datetime import datetime

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Index
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    network: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    asset_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    quote_currency: Mapped[str] = mapped_column(
        String(10),
        default="USDT",
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index(
            "ix_assets_type_active",
            "asset_type",
            "is_active"
        ),
    )
