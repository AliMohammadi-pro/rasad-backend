from datetime import timezone
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pydantic import BaseModel, Field

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User
from app.models.asset import Asset
from app.models.wallet_balance import WalletBalance
from app.models.transaction import Transaction
from app.models.deposit import Deposit
from app.models.withdrawal import Withdrawal

from app.utils.auth import get_current_user

from app.services.wallet_service import (
    get_or_create_wallet,
    get_daily_deposit_amount,
    create_deposit,
    get_latest_price,
    execute_buy,
    execute_sell,
    execute_withdrawal,
    is_tradeable_asset,
    TRADING_FEE_RATE,
    WITHDRAWAL_FEE_RATE,
    MAX_DAILY_DEPOSIT,
    MAX_WITHDRAWAL_VALUE_USDT
)


router = APIRouter(
    prefix="/api/trading",
    tags=["Trading"]
)


# ==================================================
# Schemas
# ==================================================

class DepositRequest(BaseModel):
    amount_usdt: Decimal = Field(
        gt=0,
        max_digits=30,
        decimal_places=10
    )


class BuyRequest(BaseModel):
    symbol: str

    spend_usdt: Decimal = Field(
        gt=0,
        max_digits=30,
        decimal_places=10
    )


class SellRequest(BaseModel):
    symbol: str

    quantity: Decimal = Field(
        gt=0,
        max_digits=30,
        decimal_places=18
    )


class WithdrawRequest(BaseModel):
    symbol: str

    quantity: Decimal = Field(
        gt=0,
        max_digits=30,
        decimal_places=18
    )


# ==================================================
# Wallet
# ==================================================

@router.get("/wallet")
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    wallet = get_or_create_wallet(
        db,
        current_user
    )

    db.commit()

    return {
        "user_id": current_user.id,
        "balance_usdt": wallet.balance_usdt,
        "trading_fee_rate": TRADING_FEE_RATE
    }


# ==================================================
# Wallet Summary
# ==================================================

@router.get("/wallet/summary")
def get_wallet_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    wallet = get_or_create_wallet(
        db,
        current_user
    )

    db.commit()

    result = db.execute(
        select(
            WalletBalance,
            Asset
        )
        .join(
            Asset,
            WalletBalance.asset_id == Asset.id
        )
        .where(
            WalletBalance.user_id == current_user.id,
            WalletBalance.quantity > 0,
            Asset.is_active == True
        )
        .order_by(
            Asset.symbol
        )
    )

    rows = result.all()

    assets = []

    total_assets_value = Decimal("0")

    for wallet_balance, asset in rows:

        market_price = get_latest_price(
            db,
            asset
        )

        if not market_price:
            continue

        quantity = Decimal(
            str(wallet_balance.quantity)
        )

        price = Decimal(
            str(market_price.price)
        )

        value_usdt = quantity * price

        total_assets_value += value_usdt

        assets.append({
            "asset_id": asset.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "network": asset.network,
            "asset_type": asset.asset_type,
            "quote_currency": asset.quote_currency,
            "quantity": quantity,
            "current_price": price,
            "value_usdt": value_usdt,
            "change_24h": market_price.change_24h,
            "recorded_at": market_price.recorded_at
        })

    usdt_balance = Decimal(
        str(wallet.balance_usdt)
    )

    total_wallet_value = (
        usdt_balance
        + total_assets_value
    )

    return {
        "user_id": current_user.id,
        "balance_usdt": usdt_balance,
        "assets_value_usdt": total_assets_value,
        "total_wallet_value_usdt": total_wallet_value,
        "trading_fee_rate": TRADING_FEE_RATE,
        "assets": assets
    }


# ==================================================
# Deposit USDT
# ==================================================

@router.post("/deposit")
def deposit_usdt(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    amount = Decimal(
        str(data.amount_usdt)
    )

    try:

        deposit = create_deposit(
            db,
            current_user,
            amount
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    wallet = get_or_create_wallet(
        db,
        current_user
    )

    db.commit()

    daily_amount = get_daily_deposit_amount(
        db,
        current_user.id
    )

    remaining = (
        MAX_DAILY_DEPOSIT
        - daily_amount
    )

    if remaining < 0:
        remaining = Decimal("0")

    return {
        "message": "USDT deposited successfully",
        "deposit_id": deposit.id,
        "amount_usdt": amount,
        "daily_deposited_usdt": daily_amount,
        "daily_limit_usdt": MAX_DAILY_DEPOSIT,
        "remaining_today_usdt": remaining,
        "wallet_balance_usdt": wallet.balance_usdt
    }


# ==================================================
# Deposit History
# ==================================================

@router.get("/deposits")
def get_deposits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    result = db.execute(
        select(Deposit)
        .where(
            Deposit.user_id == current_user.id
        )
        .order_by(
            desc(Deposit.created_at)
        )
    )

    deposits = result.scalars().all()

    return {
    "count": len(deposits),
    "data": [
        {
            "id": deposit.id,
            "amount_usdt": deposit.amount_usdt,
            "created_at": (
                deposit.created_at.replace(
                    tzinfo=timezone.utc
                )
                if deposit.created_at
                else None
            )
        }
        for deposit in deposits
    ]
}


# ==================================================
# Daily Deposit Limit
# ==================================================

@router.get("/deposit-limit")
def deposit_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    deposited = get_daily_deposit_amount(
        db,
        current_user.id
    )

    remaining = (
        MAX_DAILY_DEPOSIT
        - deposited
    )

    if remaining < 0:
        remaining = Decimal("0")

    return {
        "daily_limit_usdt": MAX_DAILY_DEPOSIT,
        "deposited_today_usdt": deposited,
        "remaining_today_usdt": remaining
    }


# ==================================================
# WITHDRAW
# ==================================================

@router.post("/withdraw")
def withdraw_asset(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    symbol = data.symbol.strip().upper()
    quantity = Decimal(str(data.quantity))

    if symbol == "USDT":
        try:
            withdrawal = execute_withdrawal(
                db,
                current_user,
                None,
                quantity,
                Decimal("1")
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        wallet = get_or_create_wallet(db, current_user)
        return {
            "message": "USDT withdrawal simulated successfully",
            "withdrawal_id": withdrawal.id,
            "symbol": withdrawal.symbol,
            "name": withdrawal.name,
            "network": withdrawal.network,
            "quantity": withdrawal.quantity,
            "fee_quantity": withdrawal.fee_quantity,
            "received_quantity": withdrawal.received_quantity,
            "price": withdrawal.price,
            "gross_usdt": withdrawal.gross_usdt,
            "fee_usdt": withdrawal.fee_usdt,
            "remaining_balance_usdt": wallet.balance_usdt,
            "fee_rate": WITHDRAWAL_FEE_RATE,
            "max_withdrawal_value_usdt": MAX_WITHDRAWAL_VALUE_USDT
        }

    asset = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active == True
        )
    ).scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    market_price = get_latest_price(db, asset)

    if not market_price:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Market price is not available"
        )

    try:
        withdrawal = execute_withdrawal(
            db,
            current_user,
            asset,
            quantity,
            Decimal(str(market_price.price))
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {
        "message": "Asset withdrawal simulated successfully",
        "withdrawal_id": withdrawal.id,
        "symbol": withdrawal.symbol,
        "name": withdrawal.name,
        "network": withdrawal.network,
        "quantity": withdrawal.quantity,
        "fee_quantity": withdrawal.fee_quantity,
        "received_quantity": withdrawal.received_quantity,
        "price": withdrawal.price,
        "gross_usdt": withdrawal.gross_usdt,
        "fee_usdt": withdrawal.fee_usdt,
        "fee_rate": WITHDRAWAL_FEE_RATE,
        "max_withdrawal_value_usdt": MAX_WITHDRAWAL_VALUE_USDT
    }


@router.get("/withdrawals")
def get_withdrawals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        select(Withdrawal)
        .where(
            Withdrawal.user_id == current_user.id
        )
        .order_by(
            desc(Withdrawal.created_at)
        )
    )
    withdrawals = result.scalars().all()
    return {
        "count": len(withdrawals),
        "data": [
            {
                "id": withdrawal.id,
                "symbol": withdrawal.symbol,
                "name": withdrawal.name,
                "network": withdrawal.network,
                "quantity": withdrawal.quantity,
                "price": withdrawal.price,
                "gross_usdt": withdrawal.gross_usdt,
                "fee_quantity": withdrawal.fee_quantity,
                "fee_usdt": withdrawal.fee_usdt,
                "received_quantity": withdrawal.received_quantity,
                "created_at": withdrawal.created_at
            }
            for withdrawal in withdrawals
        ]
    }


# ==================================================
# BUY
# ==================================================

@router.post("/buy")
def buy_asset(
    data: BuyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    symbol = data.symbol.strip().upper()

    # ----------------------------------------------
    # Find asset
    # ----------------------------------------------

    asset = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active == True
        )
    ).scalar_one_or_none()

    if not asset:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    # ----------------------------------------------
    # Check if asset is tradeable
    # ----------------------------------------------

    if not is_tradeable_asset(asset):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This asset is not available for trading"
        )

    # ----------------------------------------------
    # Latest market price
    # ----------------------------------------------

    market_price = get_latest_price(
        db,
        asset
    )

    if not market_price:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Market price is not available"
        )

    spend_usdt = Decimal(
        str(data.spend_usdt)
    )

    price = Decimal(
        str(market_price.price)
    )

    try:

        transaction = execute_buy(
            db,
            current_user,
            asset,
            spend_usdt,
            price
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    gross_amount = Decimal(
        str(transaction.total_usdt)
    )

    fee = Decimal(
        str(transaction.fee_usdt)
    )

    total_spent = (
        gross_amount + fee
    )

    return {
        "message": "Buy order executed successfully",
        "transaction_id": transaction.id,
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "unit": "XAU" if asset.symbol == "GOLD" else asset.symbol,
        "type": "BUY",
        "quantity": transaction.quantity,
        "price": transaction.price,
        "gross_usdt": gross_amount,
        "fee_usdt": fee,
        "total_spent_usdt": total_spent
    }


# ==================================================
# SELL
# ==================================================

@router.post("/sell")
def sell_asset(
    data: SellRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    symbol = data.symbol.strip().upper()

    # ----------------------------------------------
    # Find asset
    # ----------------------------------------------

    asset = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active == True
        )
    ).scalar_one_or_none()

    if not asset:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    # ----------------------------------------------
    # Check if asset is tradeable
    # ----------------------------------------------

    if not is_tradeable_asset(asset):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This asset is not available for trading"
        )

    # ----------------------------------------------
    # Latest market price
    # ----------------------------------------------

    market_price = get_latest_price(
        db,
        asset
    )

    if not market_price:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Market price is not available"
        )

    quantity = Decimal(
        str(data.quantity)
    )

    price = Decimal(
        str(market_price.price)
    )

    try:

        transaction = execute_sell(
            db,
            current_user,
            asset,
            quantity,
            price
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    gross_amount = Decimal(
        str(transaction.total_usdt)
    )

    fee = Decimal(
        str(transaction.fee_usdt)
    )

    received = (
        gross_amount - fee
    )

    return {
        "message": "Sell order executed successfully",
        "transaction_id": transaction.id,
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "unit": "XAU" if asset.symbol == "GOLD" else asset.symbol,
        "type": "SELL",
        "quantity": transaction.quantity,
        "price": transaction.price,
        "gross_usdt": gross_amount,
        "fee_usdt": fee,
        "received_usdt": received
    }


# ==================================================
# Transactions
# ==================================================

@router.get("/transactions")
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    result = db.execute(
        select(
            Transaction,
            Asset
        )
        .join(
            Asset,
            Transaction.asset_id == Asset.id
        )
        .where(
            Transaction.user_id == current_user.id
        )
        .order_by(
            desc(Transaction.created_at)
        )
    )

    rows = result.all()

    return {
        "count": len(rows),
        "data": [
            {
                "id": transaction.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "network": asset.network,
                "asset_type": asset.asset_type,
                "quote_currency": asset.quote_currency,
                "unit": (
                    "XAU"
                    if asset.symbol == "GOLD"
                    else asset.symbol
                ),
                "type": transaction.transaction_type,
                "quantity": transaction.quantity,
                "price": transaction.price,
                "total_usdt": transaction.total_usdt,
                "fee_usdt": transaction.fee_usdt,
                "created_at": transaction.created_at
            }
            for transaction, asset in rows
        ]
    }


# ==================================================
# Holdings
# ==================================================

@router.get("/holdings")
def get_holdings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.portfolio_service import get_portfolio
    portfolio = get_portfolio(db, current_user)
    holdings = []
    for asset in portfolio.get("assets", []):
        quantity = Decimal(str(asset.get("quantity", 0)))
        if quantity <= 0:
            continue
        holdings.append({
            "asset_id": asset.get("asset_id"),
            "symbol": asset.get("symbol"),
            "name": asset.get("name"),
            "network": asset.get("network"),
            "asset_type": asset.get("asset_type"),
            "quote_currency": asset.get("quote_currency"),
            "unit": asset.get("unit"),
            "quantity": quantity,
            "current_price": asset.get("current_price", Decimal("0")),
            "current_value_usdt": asset.get("current_value_usdt", Decimal("0")),
            "average_buy_price": asset.get("average_buy_price", Decimal("0")),
            "cost_basis_usdt": asset.get("cost_basis_usdt", Decimal("0")),
            "realized_pnl_usdt": asset.get("realized_pnl_usdt", Decimal("0")),
            "unrealized_pnl_usdt": asset.get("unrealized_pnl_usdt", Decimal("0")),
            "total_pnl_usdt": asset.get("total_pnl_usdt", Decimal("0")),
            "change_24h": asset.get("change_24h", Decimal("0")),
            "recorded_at": asset.get("recorded_at")
        })
    holdings.sort(key=lambda item: item.get("symbol") or "")
    return {
        "count": len(holdings),
        "data": holdings
    }

