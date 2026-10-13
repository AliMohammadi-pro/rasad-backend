from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
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

    # PRICE_ABOVE
    # PRICE_BELOW
    # CHANGE_24H_ABOVE
    # CHANGE_24H_BELOW
    alert_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False
    )

    target_value: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    is_triggered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Value at the moment the alert triggered.
    triggered_value: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    # Price at the moment the alert triggered.
    triggered_price: Mapped[Decimal | None] = mapped_column(
        Numeric(30, 10),
        nullable=True
    )

    # Used by the future frontend so a browser
    # notification is not shown repeatedly.
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


Index(
    "ix_alerts_user_active",
    Alert.user_id,
    Alert.is_active
)

Index(
    "ix_alerts_asset_active",
    Alert.asset_id,
    Alert.is_active
)