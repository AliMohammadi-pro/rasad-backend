from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User

from app.utils.auth import get_current_user

from app.services.portfolio_service import (
    get_portfolio
)

from app.services.portfolio_snapshot_service import (
    create_portfolio_snapshot,
    get_portfolio_history
)


router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"]
)


# ==================================================
# Current Portfolio
# ==================================================

@router.get("")
def portfolio(

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return get_portfolio(
        db,
        current_user
    )


# ==================================================
# Create Portfolio Snapshot
# ==================================================

@router.post("/snapshot")
def create_snapshot(

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    snapshot = create_portfolio_snapshot(
        db,
        current_user
    )

    return {
        "message": "Portfolio snapshot created",

        "snapshot": {
            "id": snapshot.id,

            "balance_usdt":
                snapshot.balance_usdt,

            "crypto_value_usdt":
                snapshot.crypto_value_usdt,

            "total_wallet_value_usdt":
                snapshot.total_wallet_value_usdt,

            "total_cost_basis_usdt":
                snapshot.total_cost_basis_usdt,

            "realized_pnl_usdt":
                snapshot.realized_pnl_usdt,

            "unrealized_pnl_usdt":
                snapshot.unrealized_pnl_usdt,

            "total_pnl_usdt":
                snapshot.total_pnl_usdt,

            "pnl_percentage":
                snapshot.pnl_percentage,

            "recorded_at":
                snapshot.recorded_at
        }
    }


# ==================================================
# Portfolio History
# ==================================================

@router.get("/history")
def portfolio_history(

    period: str = Query(
        default="24h"
    ),

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    try:

        snapshots = get_portfolio_history(
            db,
            current_user,
            period
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return {
        "period": period,

        "count": len(snapshots),

        "data": [
            {
                "recorded_at":
                    snapshot.recorded_at,

                "balance_usdt":
                    snapshot.balance_usdt,

                "crypto_value_usdt":
                    snapshot.crypto_value_usdt,

                "total_wallet_value_usdt":
                    snapshot.total_wallet_value_usdt,

                "total_cost_basis_usdt":
                    snapshot.total_cost_basis_usdt,

                "realized_pnl_usdt":
                    snapshot.realized_pnl_usdt,

                "unrealized_pnl_usdt":
                    snapshot.unrealized_pnl_usdt,

                "total_pnl_usdt":
                    snapshot.total_pnl_usdt,

                "pnl_percentage":
                    snapshot.pnl_percentage
            }

            for snapshot in snapshots
        ]
    }