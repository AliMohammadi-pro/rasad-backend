from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.portfolio_service import get_portfolio


def create_portfolio_snapshot(
    db: Session,
    user: User
) -> PortfolioSnapshot:

    portfolio = get_portfolio(
        db,
        user
    )

    snapshot = PortfolioSnapshot(
        user_id=user.id,

        balance_usdt=Decimal(
            str(portfolio["balance_usdt"])
        ),

        crypto_value_usdt=Decimal(
            str(portfolio["crypto_value_usdt"])
        ),

        total_wallet_value_usdt=Decimal(
            str(portfolio["total_wallet_value_usdt"])
        ),

        total_cost_basis_usdt=Decimal(
            str(portfolio["total_cost_basis_usdt"])
        ),

        realized_cost_basis_usdt=Decimal(
            str(portfolio["realized_cost_basis_usdt"])
        ),

        realized_pnl_usdt=Decimal(
            str(portfolio["realized_pnl_usdt"])
        ),

        unrealized_pnl_usdt=Decimal(
            str(portfolio["unrealized_pnl_usdt"])
        ),

        total_pnl_usdt=Decimal(
            str(portfolio["total_pnl_usdt"])
        ),

        pnl_percentage=Decimal(
            str(portfolio["pnl_percentage"])
        )
    )

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return snapshot


def get_portfolio_history(
    db: Session,
    user: User,
    period: str = "24h"
) -> list[PortfolioSnapshot]:

    now = datetime.now(timezone.utc)

    periods = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "1y": timedelta(days=365),
        "all": None
    }

    if period not in periods:
        raise ValueError(
            "Invalid period. "
            "Use: 1h, 6h, 24h, 7d, 30d, 1y or all."
        )

    query = (
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.user_id == user.id
        )
        .order_by(
            PortfolioSnapshot.recorded_at.asc()
        )
    )

    if periods[period] is not None:

        start_time = (
            now - periods[period]
        )

        query = query.where(
            PortfolioSnapshot.recorded_at >= start_time
        )

    result = db.execute(query)

    return result.scalars().all()


def cleanup_old_snapshots(
    db: Session,
    user: User,
    keep_days: int = 365
) -> int:

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=keep_days)
    )

    result = db.execute(
        delete(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.user_id == user.id,
            PortfolioSnapshot.recorded_at < cutoff
        )
    )

    db.commit()

    return result.rowcount or 0