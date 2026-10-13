from datetime import datetime
from decimal import Decimal

from app.utils.time import (
    utc_now,
    tehran_today_start_utc
)
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.asset import Asset
from app.models.wallet import Wallet
from app.models.wallet_balance import WalletBalance
from app.models.transaction import Transaction
from app.models.market_price import MarketPrice
from app.models.deposit import Deposit
from app.models.withdrawal import Withdrawal


TRADING_FEE_RATE = Decimal("0.001")
WITHDRAWAL_FEE_RATE = Decimal("0.01")
MAX_DAILY_DEPOSIT = Decimal("200")
MAX_WITHDRAWAL_VALUE_USDT = Decimal("250")


# --------------------------------------------------
# Tradeable asset
# --------------------------------------------------

def is_tradeable_asset(asset: Asset) -> bool:

    if asset.asset_type == "crypto":
        return True

    if (
        asset.asset_type == "commodity"
        and asset.symbol == "GOLD"
    ):
        return True

    return False


# --------------------------------------------------
# Wallet
# --------------------------------------------------

def get_or_create_wallet(
    db: Session,
    user: User
) -> Wallet:

    wallet = db.execute(
        select(Wallet)
        .where(
            Wallet.user_id == user.id
        )
        .with_for_update()
    ).scalar_one_or_none()

    if wallet:
        return wallet

    wallet = Wallet(
        user_id=user.id,
        balance_usdt=Decimal("0")
    )

    db.add(wallet)
    db.flush()

    return wallet


# --------------------------------------------------
# Wallet asset balance
# --------------------------------------------------

def get_or_create_wallet_balance(
    db: Session,
    user: User,
    asset: Asset
) -> WalletBalance:

    wallet_balance = db.execute(
        select(WalletBalance)
        .where(
            WalletBalance.user_id == user.id,
            WalletBalance.asset_id == asset.id
        )
        .with_for_update()
    ).scalar_one_or_none()

    if wallet_balance:
        return wallet_balance

    wallet_balance = WalletBalance(
        user_id=user.id,
        asset_id=asset.id,
        quantity=Decimal("0")
    )

    db.add(wallet_balance)
    db.flush()

    return wallet_balance


# --------------------------------------------------
# Daily deposit amount
# --------------------------------------------------

def get_daily_deposit_amount(
    db: Session,
    user_id: int
) -> Decimal:

    start_of_day = tehran_today_start_utc()

    result = db.execute(
        select(
            func.coalesce(
                func.sum(
                    Deposit.amount_usdt
                ),
                0
            )
        )
        .where(
            Deposit.user_id == user_id,
            Deposit.created_at >= start_of_day
        )
    )

    amount = result.scalar_one()

    return Decimal(str(amount))


# --------------------------------------------------
# Deposit
# --------------------------------------------------

def create_deposit(
    db: Session,
    user: User,
    amount: Decimal
) -> Deposit:

    if amount <= 0:
        raise ValueError(
            "Deposit amount must be greater than zero"
        )

    daily_amount = get_daily_deposit_amount(
        db,
        user.id
    )

    if daily_amount + amount > MAX_DAILY_DEPOSIT:

        remaining = (
            MAX_DAILY_DEPOSIT
            - daily_amount
        )

        raise ValueError(
            "Daily deposit limit exceeded. "
            f"Remaining today: {remaining} USDT"
        )

    wallet = get_or_create_wallet(
        db,
        user
    )

    current_balance = Decimal(
        str(wallet.balance_usdt)
    )

    wallet.balance_usdt = (
        current_balance + amount
    )

    deposit = Deposit(
        user_id=user.id,
        amount_usdt=amount
    )

    db.add(deposit)

    db.commit()
    db.refresh(deposit)

    return deposit


# --------------------------------------------------
# Latest market price
# --------------------------------------------------

def get_latest_price(
    db: Session,
    asset: Asset
) -> MarketPrice | None:

    return db.execute(
        select(MarketPrice)
        .where(
            MarketPrice.asset_id == asset.id
        )
        .order_by(
            MarketPrice.recorded_at.desc()
        )
        .limit(1)
    ).scalar_one_or_none()


# --------------------------------------------------
# BUY
# --------------------------------------------------

def execute_buy(
    db: Session,
    user: User,
    asset: Asset,
    spend_usdt: Decimal,
    price: Decimal
) -> Transaction:

    if not is_tradeable_asset(asset):
        raise ValueError(
            "This asset is not available for trading"
        )

    if price <= 0:
        raise ValueError(
            "Market price must be greater than zero"
        )

    wallet = get_or_create_wallet(
        db,
        user
    )

    balance = Decimal(
        str(wallet.balance_usdt)
    )

    if spend_usdt <= 0:
        raise ValueError(
            "Buy amount must be greater than zero"
        )

    if spend_usdt > balance:
        raise ValueError(
            "Insufficient USDT balance"
        )

    # The amount entered by the user
    # includes the trading fee.

    gross_amount = (
        spend_usdt
        / (
            Decimal("1")
            + TRADING_FEE_RATE
        )
    )

    fee = (
        gross_amount
        * TRADING_FEE_RATE
    )

    quantity = (
        gross_amount
        / price
    )

    # Remove USDT
    wallet.balance_usdt = (
        balance - spend_usdt
    )

    # Add asset
    wallet_balance = (
        get_or_create_wallet_balance(
            db,
            user,
            asset
        )
    )

    current_quantity = Decimal(
        str(wallet_balance.quantity)
    )

    wallet_balance.quantity = (
        current_quantity + quantity
    )

    transaction = Transaction(
        user_id=user.id,
        asset_id=asset.id,
        transaction_type="BUY",
        quantity=quantity,
        price=price,
        total_usdt=gross_amount,
        fee_usdt=fee
    )

    db.add(transaction)

    db.commit()
    db.refresh(transaction)

    return transaction


# --------------------------------------------------
# SELL
# --------------------------------------------------

def execute_sell(
    db: Session,
    user: User,
    asset: Asset,
    quantity: Decimal,
    price: Decimal
) -> Transaction:

    if not is_tradeable_asset(asset):
        raise ValueError(
            "This asset is not available for trading"
        )

    if price <= 0:
        raise ValueError(
            "Market price must be greater than zero"
        )

    wallet = get_or_create_wallet(
        db,
        user
    )

    if quantity <= 0:
        raise ValueError(
            "Sell quantity must be greater than zero"
        )

    wallet_balance = (
        get_or_create_wallet_balance(
            db,
            user,
            asset
        )
    )

    owned_quantity = Decimal(
        str(wallet_balance.quantity)
    )

    if quantity > owned_quantity:
        raise ValueError(
            "Insufficient asset quantity"
        )

    gross_amount = (
        quantity * price
    )

    fee = (
        gross_amount
        * TRADING_FEE_RATE
    )

    received_amount = (
        gross_amount - fee
    )

    # Remove asset
    wallet_balance.quantity = (
        owned_quantity - quantity
    )

    # Add USDT
    current_usdt = Decimal(
        str(wallet.balance_usdt)
    )

    wallet.balance_usdt = (
        current_usdt + received_amount
    )

    transaction = Transaction(
        user_id=user.id,
        asset_id=asset.id,
        transaction_type="SELL",
        quantity=quantity,
        price=price,
        total_usdt=gross_amount,
        fee_usdt=fee
    )

    db.add(transaction)

    db.commit()
    db.refresh(transaction)

    return transaction

def execute_withdrawal(
    db: Session,
    user: User,
    asset: Asset | None,
    quantity: Decimal,
    price: Decimal
) -> Withdrawal:
    if quantity <= 0:
        raise ValueError("Withdrawal amount must be greater than zero")
    if price <= 0:
        raise ValueError("Market price must be greater than zero")
    gross_value_usdt = quantity * price
    if gross_value_usdt > MAX_WITHDRAWAL_VALUE_USDT:
        raise ValueError(
            f"Maximum withdrawal value is {MAX_WITHDRAWAL_VALUE_USDT} USDT"
        )
    fee_quantity = quantity * WITHDRAWAL_FEE_RATE
    net_quantity = quantity - fee_quantity
    if net_quantity <= 0:
        raise ValueError("Withdrawal amount is too small after fee")
    fee_usdt = gross_value_usdt * WITHDRAWAL_FEE_RATE
    wallet = get_or_create_wallet(db, user)
    if asset is None:
        current_balance = Decimal(str(wallet.balance_usdt))
        if quantity > current_balance:
            raise ValueError("Insufficient USDT balance")
        wallet.balance_usdt = current_balance - quantity
        symbol = "USDT"
        name = "Tether"
        network = "USDT"
        asset_id = None
    else:
        wallet_balance = get_or_create_wallet_balance(db, user, asset)
        owned_quantity = Decimal(str(wallet_balance.quantity))
        if quantity > owned_quantity:
            raise ValueError("Insufficient asset quantity")
        wallet_balance.quantity = owned_quantity - quantity
        symbol = asset.symbol
        name = asset.name
        network = asset.network
        asset_id = asset.id
    withdrawal = Withdrawal(
        user_id=user.id,
        asset_id=asset_id,
        symbol=symbol,
        name=name,
        network=network,
        quantity=quantity,
        price=price,
        gross_usdt=gross_value_usdt,
        fee_quantity=fee_quantity,
        fee_usdt=fee_usdt,
        received_quantity=net_quantity
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal
