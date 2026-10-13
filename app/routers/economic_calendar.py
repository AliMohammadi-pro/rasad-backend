from datetime import date, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.economic_calendar import (
    EconomicCalendar,
)

from app.services.economic_calendar_service import (
    IMPORTANT_COUNTRIES,
    refresh_economic_calendar,
)


router = APIRouter(
    prefix="/api/economic-calendar",
    tags=["Economic Calendar"],
)


# =========================================================
# Countries
# =========================================================

@router.get("/countries")
def get_countries():

    return {
        "count": len(IMPORTANT_COUNTRIES),
        "data": IMPORTANT_COUNTRIES,
    }


# =========================================================
# Refresh
# =========================================================

@router.post("/refresh")
def refresh_calendar(

    days: int = Query(
        30,
        ge=1,
        le=90,
    ),

    country: str = Query(
        "ALL"
    ),

    importance: str | None = Query(
        "medium"
    ),

    db: Session = Depends(get_db),
):

    try:

        return refresh_economic_calendar(
            db=db,
            days=days,
            country=country.upper(),
            importance=importance,
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


# =========================================================
# Calendar
# =========================================================

@router.get("")
def get_calendar(

    days: int = Query(
        30,
        ge=1,
        le=90,
    ),

    country: str = Query(
        "ALL"
    ),

    importance: str | None = Query(
        "medium"
    ),

    db: Session = Depends(get_db),
):

    today = date.today()

    end_date = (
        today
        + timedelta(days=days)
    )

    query = select(
        EconomicCalendar
    ).where(
        EconomicCalendar.event_date
        >= today,

        EconomicCalendar.event_date
        <= end_date,
    )

    country_value = (
        country.upper().strip()
    )

    if country_value != "ALL":

        countries = [
            item.strip().upper()
            for item in country_value.split(",")
            if item.strip()
        ]

        if countries:

            query = query.where(
                EconomicCalendar.country.in_(
                    countries
                )
            )

    if importance:

        importance_value = (
            importance.lower().strip()
        )

        if importance_value == "high":

            query = query.where(
                EconomicCalendar.importance
                == "high"
            )

        elif importance_value == "medium":

            query = query.where(
                EconomicCalendar.importance.in_(
                    [
                        "medium",
                        "high",
                    ]
                )
            )

    events = db.scalars(
        query.order_by(
            EconomicCalendar.scheduled_at.asc()
        )
    ).all()

    return {
        "count": len(events),

        "country": country_value,

        "from": today,

        "to": end_date,

        "data": [
            _serialize_event(event)
            for event in events
        ],
    }


# =========================================================
# Upcoming
# =========================================================

@router.get("/upcoming")
def upcoming_calendar(

    days: int = Query(
        7,
        ge=1,
        le=30,
    ),

    country: str = Query(
        "ALL"
    ),

    importance: str | None = Query(
        "high"
    ),

    db: Session = Depends(get_db),
):

    today = date.today()

    end_date = (
        today
        + timedelta(days=days)
    )

    query = select(
        EconomicCalendar
    ).where(
        EconomicCalendar.event_date
        >= today,

        EconomicCalendar.event_date
        <= end_date,

        EconomicCalendar.status
        == "upcoming",
    )

    country_value = (
        country.upper().strip()
    )

    if country_value != "ALL":

        countries = [
            item.strip().upper()
            for item in country_value.split(",")
            if item.strip()
        ]

        query = query.where(
            EconomicCalendar.country.in_(
                countries
            )
        )

    if importance:

        importance_value = (
            importance.lower().strip()
        )

        if importance_value == "high":

            query = query.where(
                EconomicCalendar.importance
                == "high"
            )

        elif importance_value == "medium":

            query = query.where(
                EconomicCalendar.importance.in_(
                    [
                        "medium",
                        "high",
                    ]
                )
            )

    events = db.scalars(
        query.order_by(
            EconomicCalendar.scheduled_at.asc()
        )
        .limit(100)
    ).all()

    return {
        "count": len(events),

        "country": country_value,

        "from": today,

        "to": end_date,

        "data": [
            _serialize_event(event)
            for event in events
        ],
    }


# =========================================================
# Serializer
# =========================================================

def _serialize_event(
    event: EconomicCalendar
):

    return {
        "id": event.id,

        "release_id":
            event.release_id,

        "name":
            event.release_name,

        "date":
            event.event_date,

        "scheduled_at":
            event.scheduled_at,

        "country":
            event.country,

        "currency":
            event.currency,

        "importance":
            event.importance,

        "type":
            event.event_type,

        "sector":
            event.sector,

        "unit":
            event.unit,

        "multiplier":
            event.multiplier,

        "status":
            event.status,

        "previous":
            event.previous_value,

        "forecast":
            event.forecast_value,

        "actual":
            event.actual_value,

        "revised_previous":
            event.revised_previous_value,

        "source":
            event.source,

        "source_url":
            event.source_url,

        "updated_at":
            event.updated_at,
    }