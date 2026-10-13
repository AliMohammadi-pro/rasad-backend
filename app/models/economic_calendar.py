from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class EconomicCalendar(Base):
    __tablename__ = "economic_calendar"

    id = Column(Integer, primary_key=True, index=True)

    # biquote event id is opaque and can look like: mql5:900001
    release_id = Column(String(100), nullable=False)
    release_name = Column(String(255), nullable=False)

    event_date = Column(Date, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)

    country = Column(String(10), nullable=False, default="US")
    currency = Column(String(10), nullable=True)
    importance = Column(String(20), nullable=False, default="medium")
    event_type = Column(String(30), nullable=True)
    sector = Column(String(50), nullable=True)
    unit = Column(String(50), nullable=True)
    multiplier = Column(String(30), nullable=True)

    status = Column(String(20), nullable=False, default="upcoming")

    # Keep these as strings because calendar values can contain %, K, M, etc.
    previous_value = Column(String(100), nullable=True)
    forecast_value = Column(String(100), nullable=True)
    actual_value = Column(String(100), nullable=True)
    revised_previous_value = Column(String(100), nullable=True)

    source = Column(String(50), nullable=False, default="biquote")
    source_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "event_date",
            name="uq_economic_calendar_release_date",
        ),
        Index("ix_economic_calendar_event_date", "event_date"),
        Index("ix_economic_calendar_importance", "importance"),
        Index("ix_economic_calendar_scheduled_at", "scheduled_at"),
    )
