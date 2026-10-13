from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    UniqueConstraint
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "asset_id",
            name="uq_user_watchlist_asset"
        ),
    )