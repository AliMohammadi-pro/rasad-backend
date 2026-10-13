from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import Asset
from app.services.mtf_analysis_service import analyze_multi_timeframe

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/multi/{symbol}")
def multi_timeframe_analysis(
    symbol: str,
    period: str = "30d",
    db: Session = Depends(get_db),
):
    symbol = symbol.upper().strip()
    period = period.lower().strip()

    if period not in {"24h", "7d", "30d", "90d", "1y", "all"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Allowed: 24h, 7d, 30d, 90d, 1y, all",
        )

    asset = db.execute(
        select(Asset).where(
            Asset.symbol == symbol,
            Asset.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return analyze_multi_timeframe(db, asset, period=period)
