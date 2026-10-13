from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.market_price import MarketPrice
from app.models.user import User

from app.services.notification_service import (
    build_alert_notification,
    send_fcm_notification,
)


# ==================================================
# Alert Types
# ==================================================

PRICE_ABOVE = "PRICE_ABOVE"
PRICE_BELOW = "PRICE_BELOW"
CHANGE_24H_ABOVE = "CHANGE_24H_ABOVE"
CHANGE_24H_BELOW = "CHANGE_24H_BELOW"


ALERT_TYPES = {
    PRICE_ABOVE,
    PRICE_BELOW,
    CHANGE_24H_ABOVE,
    CHANGE_24H_BELOW
}


# ==================================================
# Create Alert
# ==================================================

def create_alert(
    db: Session,
    user: User,
    asset: Asset,
    alert_type: str,
    target_value: Decimal
) -> Alert:

    if alert_type not in ALERT_TYPES:
        raise ValueError("Invalid alert type")

    if target_value <= 0:
        raise ValueError("Target value must be greater than zero")

    alert = Alert(
        user_id=user.id,
        asset_id=asset.id,
        alert_type=alert_type,
        target_value=target_value,
        is_active=True,
        is_triggered=False
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert


# ==================================================
# Get User Alerts
# ==================================================

def get_user_alerts(
    db: Session,
    user: User
) -> list[tuple[Alert, Asset]]:

    result = db.execute(
        select(Alert, Asset)
        .join(
            Asset,
            Alert.asset_id == Asset.id
        )
        .where(
            Alert.user_id == user.id
        )
        .order_by(
            Alert.created_at.desc()
        )
    )

    return result.all()


# ==================================================
# Get Active Alerts For Asset
# ==================================================

def get_active_alerts_for_asset(
    db: Session,
    asset_id: int
) -> list[Alert]:

    result = db.execute(
        select(Alert)
        .where(
            Alert.asset_id == asset_id,
            Alert.is_active.is_(True),
            Alert.is_triggered.is_(False)
        )
        .with_for_update()
    )

    return result.scalars().all()


# ==================================================
# Get Latest Prices
# ==================================================

def get_latest_prices(
    db: Session,
    asset_id: int
) -> list[MarketPrice]:

    result = db.execute(
        select(MarketPrice)
        .where(
            MarketPrice.asset_id == asset_id
        )
        .order_by(
            MarketPrice.recorded_at.desc()
        )
        .limit(2)
    )

    return result.scalars().all()


# ==================================================
# Crossing Helpers
# ==================================================

def _crossed_above(
    previous: Decimal,
    current: Decimal,
    target: Decimal
) -> bool:

    return (
        previous < target
        and current >= target
    )


def _crossed_below(
    previous: Decimal,
    current: Decimal,
    target: Decimal
) -> bool:

    return (
        previous > target
        and current <= target
    )


def _crossed_condition(
    alert_type: str,
    previous: Decimal,
    current: Decimal,
    target: Decimal
) -> bool:

    if alert_type in (
        PRICE_ABOVE,
        CHANGE_24H_ABOVE
    ):
        return _crossed_above(
            previous,
            current,
            target
        )

    if alert_type in (
        PRICE_BELOW,
        CHANGE_24H_BELOW
    ):
        return _crossed_below(
            previous,
            current,
            target
        )

    return False


# ==================================================
# Evaluate Asset Alerts
# ==================================================

def evaluate_asset_alerts(
    db: Session,
    asset_id: int
) -> int:

    alerts = get_active_alerts_for_asset(
        db,
        asset_id
    )

    if not alerts:
        return 0

    prices = get_latest_prices(
        db,
        asset_id
    )

    if len(prices) < 2:
        return 0

    current_price = prices[0]
    previous_price = prices[1]

    current_value_price = Decimal(
        str(current_price.price)
    )

    previous_value_price = Decimal(
        str(previous_price.price)
    )

    current_change = Decimal(
        str(current_price.change_24h)
    )

    previous_change = Decimal(
        str(previous_price.change_24h)
    )

    triggered_count = 0

    for alert in alerts:

        target = Decimal(
            str(alert.target_value)
        )

        # ------------------------------------------
        # Price Alert
        # ------------------------------------------

        if alert.alert_type in (
            PRICE_ABOVE,
            PRICE_BELOW
        ):

            crossed = _crossed_condition(
                alert.alert_type,
                previous_value_price,
                current_value_price,
                target
            )

            triggered_value = current_value_price

        # ------------------------------------------
        # 24h Change Alert
        # ------------------------------------------

        elif alert.alert_type in (
            CHANGE_24H_ABOVE,
            CHANGE_24H_BELOW
        ):

            crossed = _crossed_condition(
                alert.alert_type,
                previous_change,
                current_change,
                target
            )

            triggered_value = current_change

        else:
            continue

        # ------------------------------------------
        # Condition Not Reached
        # ------------------------------------------

        if not crossed:
            continue

        # ------------------------------------------
        # Trigger Alert
        # ------------------------------------------

        alert.is_triggered = True

        alert.is_active = False

        alert.triggered_at = datetime.now(
            timezone.utc
        )

        alert.triggered_value = triggered_value

        alert.triggered_price = (
            current_value_price
        )

        alert.notification_sent_at = None

        triggered_count += 1

    # ------------------------------------------
    # Save Triggered Alerts
    # ------------------------------------------

    if triggered_count > 0:
        db.commit()

    return triggered_count


# ==================================================
# Evaluate All Active Alerts
# ==================================================

def evaluate_all_active_alerts(
    db: Session
) -> int:

    result = db.execute(
        select(Alert.asset_id)
        .where(
            Alert.is_active.is_(True),
            Alert.is_triggered.is_(False)
        )
        .distinct()
    )

    asset_ids = [
        row[0]
        for row in result.all()
    ]

    total_triggered = 0

    for asset_id in asset_ids:

        try:

            total_triggered += (
                evaluate_asset_alerts(
                    db,
                    asset_id
                )
            )

        except Exception as error:

            db.rollback()

            print(
                f"[Alerts] "
                f"Asset {asset_id} "
                f"evaluation failed: "
                f"{error}"
            )

    return total_triggered


# ==================================================
# Get Unnotified Triggered Alerts
# ==================================================

def get_unnotified_triggered_alerts(
    db: Session,
    user: User
) -> list[tuple[Alert, Asset]]:

    result = db.execute(
        select(Alert, Asset)
        .join(
            Asset,
            Alert.asset_id == Asset.id
        )
        .where(
            Alert.user_id == user.id,
            Alert.is_triggered.is_(True),
            Alert.notification_sent_at.is_(None)
        )
        .order_by(
            Alert.triggered_at.desc()
        )
    )

    return result.all()


# ==================================================
# Send Pending Alert Notifications
# ==================================================

def send_pending_alert_notifications(
    db: Session
) -> int:
    """
    تمام هشدارهای Trigger شده ولی ارسال‌نشده
    را از طریق Firebase Cloud Messaging ارسال می‌کند.

    اگر برای کاربر FCM Token وجود نداشته باشد
    یا ارسال FCM ناموفق باشد، notification_sent_at
    خالی باقی می‌ماند تا در اجرای بعدی دوباره تلاش شود.
    """

    result = db.execute(
        select(Alert, Asset)
        .join(
            Asset,
            Alert.asset_id == Asset.id
        )
        .where(
            Alert.is_triggered.is_(True),
            Alert.notification_sent_at.is_(None)
        )
        .order_by(
            Alert.triggered_at.asc()
        )
        .limit(100)
    )

    rows = result.all()

    sent_count = 0

    for alert, asset in rows:

        try:

            # --------------------------------------
            # Build Notification
            # --------------------------------------

            title, message = (
                build_alert_notification(
                    symbol=asset.symbol,
                    name=asset.name,
                    alert_type=alert.alert_type,
                    target_value=Decimal(
                        str(alert.target_value)
                    ),
                    triggered_value=Decimal(
                        str(alert.triggered_value)
                    ),
                )
            )

            # --------------------------------------
            # Send Through Firebase FCM
            # --------------------------------------

            sent = send_fcm_notification(
                user_id=alert.user_id,
                title=title,
                message=message,
                priority="high",
            )

            # --------------------------------------
            # If FCM Failed
            # --------------------------------------

            if not sent:

                print(
                    f"[FCM] "
                    f"Alert {alert.id} "
                    f"notification was not sent."
                )

                continue

            # --------------------------------------
            # Mark Notification As Sent
            # --------------------------------------

            alert.notification_sent_at = (
                datetime.now(timezone.utc)
            )

            sent_count += 1

            db.commit()

            print(
                f"[FCM] "
                f"Alert {alert.id} "
                f"notification sent successfully."
            )

        except Exception as error:

            db.rollback()

            print(
                f"[FCM] "
                f"Alert {alert.id} "
                f"notification failed: "
                f"{error}"
            )

    return sent_count


# ==================================================
# Mark Notification As Sent
# ==================================================

def mark_notification_sent(
    db: Session,
    user: User,
    alert_id: int
) -> Alert | None:

    result = db.execute(
        select(Alert)
        .where(
            Alert.id == alert_id,
            Alert.user_id == user.id
        )
        .with_for_update()
    )

    alert = result.scalar_one_or_none()

    if not alert:
        return None

    alert.notification_sent_at = (
        datetime.now(timezone.utc)
    )

    db.commit()

    db.refresh(alert)

    return alert


# ==================================================
# Delete Alert
# ==================================================

def delete_alert(
    db: Session,
    user: User,
    alert_id: int
) -> bool:

    result = db.execute(
        select(Alert)
        .where(
            Alert.id == alert_id,
            Alert.user_id == user.id
        )
        .with_for_update()
    )

    alert = result.scalar_one_or_none()

    if not alert:
        return False

    db.delete(alert)

    db.commit()

    return True


# ==================================================
# Deactivate Alert
# ==================================================

def deactivate_alert(
    db: Session,
    user: User,
    alert_id: int
) -> Alert | None:

    result = db.execute(
        select(Alert)
        .where(
            Alert.id == alert_id,
            Alert.user_id == user.id
        )
        .with_for_update()
    )

    alert = result.scalar_one_or_none()

    if not alert:
        return None

    alert.is_active = False

    db.commit()

    db.refresh(alert)

    return alert