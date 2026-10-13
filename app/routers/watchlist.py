from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pydantic import BaseModel

from sqlalchemy import (
    select,
    desc
)

from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User
from app.models.asset import Asset
from app.models.watchlist import Watchlist
from app.models.market_price import MarketPrice

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/watchlist",
    tags=["Watchlist"]
)


# ==================================================
# Schema
# ==================================================

class WatchlistRequest(BaseModel):
    symbol: str


# ==================================================
# Get user's watchlist
# ==================================================

@router.get("")
def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(
            Watchlist,
            Asset
        )
        .join(
            Asset,
            Watchlist.asset_id == Asset.id
        )
        .where(
            Watchlist.user_id == current_user.id,
            Asset.is_active == True
        )
        .order_by(
            Watchlist.created_at.desc()
        )
    )

    rows = result.all()

    data = []

    for watchlist_item, asset in rows:

        price_result = db.execute(
            select(MarketPrice)
            .where(
                MarketPrice.asset_id == asset.id
            )
            .order_by(
                desc(MarketPrice.recorded_at)
            )
            .limit(1)
        )

        market_price = (
            price_result.scalars().first()
        )

        data.append({
            "watchlist_id": watchlist_item.id,

            "asset_id": asset.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "network": asset.network,
            "asset_type": asset.asset_type,
            "quote_currency": asset.quote_currency,

            "price": (
                market_price.price
                if market_price
                else None
            ),

            "change_24h": (
                market_price.change_24h
                if market_price
                else None
            ),

            "volume_24h": (
                market_price.volume_24h
                if market_price
                else None
            ),

            "market_cap": (
                market_price.market_cap
                if market_price
                else None
            ),

            "recorded_at": (
                market_price.recorded_at
                if market_price
                else None
            ),

            "created_at": watchlist_item.created_at
        })

    return {
        "count": len(data),
        "data": data
    }


# ==================================================
# Add asset to watchlist
# ==================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def add_to_watchlist(
    data: WatchlistRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    symbol = data.symbol.strip().upper()

    if not symbol:
        raise HTTPException(
            status_code=400,
            detail="Symbol is required"
        )

    # --------------------------------------------------
    # Find asset
    # --------------------------------------------------

    asset_result = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active == True
        )
    )

    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    # --------------------------------------------------
    # Check duplicate
    # --------------------------------------------------

    existing_result = db.execute(
        select(Watchlist)
        .where(
            Watchlist.user_id == current_user.id,
            Watchlist.asset_id == asset.id
        )
    )

    existing = (
        existing_result
        .scalar_one_or_none()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Asset is already in watchlist"
        )

    # --------------------------------------------------
    # Create watchlist item
    # --------------------------------------------------

    item = Watchlist(
        user_id=current_user.id,
        asset_id=asset.id
    )

    db.add(item)

    try:
        db.commit()
        db.refresh(item)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Asset is already in watchlist"
        )

    return {
        "message": "Asset added to watchlist",
        "watchlist_id": item.id,
        "symbol": asset.symbol,
        "name": asset.name
    }


# ==================================================
# Remove asset from watchlist
# ==================================================

@router.delete("/{symbol}")
def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    symbol = symbol.strip().upper()

    asset_result = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active == True
        )
    )

    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    item_result = db.execute(
        select(Watchlist)
        .where(
            Watchlist.user_id == current_user.id,
            Watchlist.asset_id == asset.id
        )
    )

    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Asset is not in watchlist"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Asset removed from watchlist",
        "symbol": asset.symbol
    }