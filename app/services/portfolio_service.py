from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.asset import Asset
from app.models.wallet import Wallet
from app.models.wallet_balance import WalletBalance
from app.models.transaction import Transaction
from app.models.withdrawal import Withdrawal
from app.services.wallet_service import get_latest_price


ZERO = Decimal("0")


def get_portfolio(
    db: Session,
    user: User
) -> dict:

    # ==================================================
    # Wallet
    # ==================================================

    wallet = db.execute(
        select(Wallet)
        .where(
            Wallet.user_id == user.id
        )
    ).scalar_one_or_none()

    usdt_balance = ZERO

    if wallet:
        usdt_balance = Decimal(
            str(wallet.balance_usdt)
        )

    # ==================================================
    # Wallet balances
    #
    # IMPORTANT:
    # We intentionally do NOT filter quantity > 0 here.
    #
    # Why?
    # A completely sold asset can have quantity = 0,
    # but it may still have realized P/L.
    # ==================================================

    balances_result = db.execute(
        select(
            WalletBalance,
            Asset
        )
        .join(
            Asset,
            WalletBalance.asset_id == Asset.id
        )
        .where(
            WalletBalance.user_id == user.id,
            Asset.is_active == True
        )
    )

    balances = balances_result.all()

    assets = []

    total_crypto_value = ZERO
    total_realized_pnl = ZERO
    total_unrealized_pnl = ZERO

    # Cost basis of currently held assets
    current_cost_basis = ZERO

    # Cost basis of sold assets
    realized_cost_basis = ZERO

    # ==================================================
    # Process assets
    # ==================================================

    for wallet_balance, asset in balances:

        current_quantity = Decimal(
            str(wallet_balance.quantity)
        )

        # --------------------------------------------------
        # Get all transactions for this asset
        # --------------------------------------------------

        transactions_result = db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user.id,
                Transaction.asset_id == asset.id
            )
            .order_by(
                Transaction.created_at.asc(),
                Transaction.id.asc()
            )
        )

        transactions = transactions_result.scalars().all()

        withdrawals_result = db.execute(
            select(Withdrawal)
            .where(
                Withdrawal.user_id == user.id,
                Withdrawal.asset_id == asset.id
            )
            .order_by(
                Withdrawal.created_at.asc(),
                Withdrawal.id.asc()
            )
        )

        withdrawals = withdrawals_result.scalars().all()

        if not transactions and not withdrawals:
            continue

        events = []

        for transaction in transactions:
            events.append(
                (
                    transaction.created_at,
                    0,
                    transaction.id,
                    "transaction",
                    transaction
                )
            )

        for withdrawal in withdrawals:
            events.append(
                (
                    withdrawal.created_at,
                    1,
                    withdrawal.id,
                    "withdrawal",
                    withdrawal
                )
            )

        events.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2]
            )
        )

        running_quantity = ZERO
        running_cost = ZERO
        realized_pnl = ZERO
        asset_realized_cost = ZERO

        for _, _, _, event_type, event in events:

            if event_type == "withdrawal":
                quantity = Decimal(
                    str(event.quantity)
                )

                if quantity <= ZERO or running_quantity <= ZERO:
                    continue

                if quantity > running_quantity:
                    quantity = running_quantity

                average_cost = (
                    running_cost
                    / running_quantity
                )

                cost_of_withdrawal = (
                    average_cost
                    * quantity
                )

                running_quantity -= quantity
                running_cost -= cost_of_withdrawal

                if abs(running_quantity) < Decimal(
                    "0.000000000000000001"
                ):
                    running_quantity = ZERO

                if abs(running_cost) < Decimal(
                    "0.00000001"
                ):
                    running_cost = ZERO

                continue

            transaction = event

            quantity = Decimal(
                str(transaction.quantity)
            )

            fee = Decimal(
                str(transaction.fee_usdt)
            )

            price = Decimal(
                str(transaction.price)
            )

            if transaction.transaction_type == "BUY":
                buy_cost = (
                    Decimal(
                        str(transaction.total_usdt)
                    )
                    + fee
                )

                running_quantity += quantity
                running_cost += buy_cost

            elif transaction.transaction_type == "SELL":

                if running_quantity <= ZERO:
                    continue

                average_cost = (
                    running_cost
                    / running_quantity
                )

                cost_of_sold = (
                    average_cost
                    * quantity
                )

                gross_proceeds = (
                    quantity * price
                )

                net_proceeds = (
                    gross_proceeds - fee
                )

                sale_pnl = (
                    net_proceeds
                    - cost_of_sold
                )

                realized_pnl += sale_pnl
                asset_realized_cost += cost_of_sold

                running_quantity -= quantity
                running_cost -= cost_of_sold

                if abs(running_quantity) < Decimal(
                    "0.000000000000000001"
                ):
                    running_quantity = ZERO

                if abs(running_cost) < Decimal(
                    "0.00000001"
                ):
                    running_cost = ZERO


        # Current market price
        # --------------------------------------------------

        market_price = get_latest_price(
            db,
            asset
        )

        current_price = ZERO
        current_value = ZERO
        unrealized_pnl = ZERO

        if market_price:

            current_price = Decimal(
                str(market_price.price)
            )

            current_value = (
                current_quantity
                * current_price
            )

            if current_quantity > ZERO:

                unrealized_pnl = (
                    current_value
                    - running_cost
                )

        # --------------------------------------------------
        # Average buy price
        # --------------------------------------------------

        average_buy_price = ZERO

        if current_quantity > ZERO:

            average_buy_price = (
                running_cost
                / current_quantity
            )

        # --------------------------------------------------
        # Totals
        # --------------------------------------------------

        total_crypto_value += current_value

        total_realized_pnl += realized_pnl

        total_unrealized_pnl += unrealized_pnl

        current_cost_basis += running_cost

        realized_cost_basis += asset_realized_cost

        # --------------------------------------------------
        # Only show assets that are currently held
        # OR have realized P/L.
        # --------------------------------------------------

        if (
            current_quantity > ZERO
            or realized_pnl != ZERO
        ):

            assets.append({
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "network": asset.network,
                "asset_type": asset.asset_type,
                "quote_currency": asset.quote_currency,
                "unit": "XAU" if asset.symbol == "GOLD" else asset.symbol,

                "quantity": current_quantity,

                "current_price": current_price,

                "current_value_usdt": current_value,

                "average_buy_price": average_buy_price,

                "cost_basis_usdt": running_cost,

                "realized_pnl_usdt": realized_pnl,

                "unrealized_pnl_usdt": unrealized_pnl,

                "total_pnl_usdt": (
                    realized_pnl
                    + unrealized_pnl
                ),

                "change_24h": (
                    market_price.change_24h
                    if market_price
                    else ZERO
                ),

                "recorded_at": (
                    market_price.recorded_at
                    if market_price
                    else None
                )
            })

    # ==================================================
    # Portfolio totals
    # ==================================================

    total_wallet_value = (
        usdt_balance
        + total_crypto_value
    )

    total_pnl = (
        total_realized_pnl
        + total_unrealized_pnl
    )

    # ==================================================
    # P/L percentage
    #
    # Include both:
    # - cost of currently held assets
    # - cost of assets already sold
    # ==================================================

    total_performance_basis = (
        current_cost_basis
        + realized_cost_basis
    )

    if total_performance_basis > ZERO:

        pnl_percentage = (
            total_pnl
            / total_performance_basis
        ) * Decimal("100")

    else:

        pnl_percentage = ZERO

    return {
        "balance_usdt": usdt_balance,

        "crypto_value_usdt": total_crypto_value,

        "total_wallet_value_usdt": total_wallet_value,

        "total_cost_basis_usdt": current_cost_basis,

        "realized_cost_basis_usdt": realized_cost_basis,

        "realized_pnl_usdt": total_realized_pnl,

        "unrealized_pnl_usdt": total_unrealized_pnl,

        "total_pnl_usdt": total_pnl,

        "pnl_percentage": pnl_percentage,

        "assets": assets
    }