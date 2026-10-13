from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.asset import Asset
from app.services.seed_service import seed_assets


router = APIRouter(
    prefix="/api/market",
    tags=["Market"]
)


@router.post("/seed")
def seed_market_assets(
    db: Session = Depends(get_db)
):
    seed_assets(db)

    return {
        "message": "Market assets seeded successfully"
    }


@router.get("/assets")
def get_assets(
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(Asset)
        .where(Asset.is_active == True)
        .order_by(
            Asset.asset_type,
            Asset.symbol
        )
    )

    assets = result.scalars().all()

    return [
        {
            "id": asset.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "network": asset.network,
            "asset_type": asset.asset_type,
            "quote_currency": asset.quote_currency
        }
        for asset in assets
    ]