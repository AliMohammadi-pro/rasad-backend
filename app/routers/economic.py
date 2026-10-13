from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.economic_indicator import (
    EconomicIndicator
)

from app.services.economic_data_service import (
    SUPPORTED_INDICATORS,
    fetch_indicator,
    save_indicator,
)


router = APIRouter(
    prefix="/api/economic",
    tags=["Economic"]
)


@router.get("/supported")
def supported_indicators():

    return {
        "data": list(
            SUPPORTED_INDICATORS.keys()
        )
    }


@router.post(
    "/refresh/{indicator}"
)
def refresh_indicator(
    indicator: str,
    db: Session = Depends(get_db)
):

    indicator = indicator.upper()

    if indicator not in SUPPORTED_INDICATORS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported economic indicator"
            )
        )

    try:

        rows = fetch_indicator(
            indicator
        )

        saved = save_indicator(
            db,
            indicator,
            rows
        )

        return {
            "indicator": indicator,
            "received": len(rows),
            "saved": saved
        }

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )


@router.get(
    "/{indicator}"
)
def get_indicator(
    indicator: str,
    db: Session = Depends(get_db)
):

    indicator = indicator.upper()

    if indicator not in SUPPORTED_INDICATORS:

        raise HTTPException(
            status_code=404,
            detail="Indicator not supported"
        )

    rows = db.execute(
        select(EconomicIndicator)
        .where(
            EconomicIndicator.indicator
            == indicator
        )
        .order_by(
            desc(EconomicIndicator.date)
        )
        .limit(100)
    ).scalars().all()

    return {
        "indicator": indicator,
        "count": len(rows),
        "data": [
            {
                "date": row.date,
                "value": (
                    float(row.value)
                    if row.value is not None
                    else None
                ),
                "unit": row.unit,
                "source": row.source,
            }
            for row in rows
        ]
    }