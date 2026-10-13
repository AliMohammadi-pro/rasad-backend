from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from pydantic import BaseModel, Field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.user import User
from app.models.asset import Asset

from app.utils.auth import get_current_user

from app.services.notification_service import (
    get_user_topic,
    get_user_topic_url,
    send_ntfy_notification,
)

from app.services.push_token_service import (
    register_push_token,
    remove_push_token,
)

from app.services.alert_service import (
    create_alert,
    get_user_alerts,
    get_unnotified_triggered_alerts,
    mark_notification_sent,
    delete_alert,
    deactivate_alert,
    ALERT_TYPES
)


router = APIRouter(
    prefix="/api/alerts",
    tags=["Alerts"]
)


# ==================================================
# Schemas
# ==================================================

class CreateAlertRequest(BaseModel):

    symbol: str

    alert_type: str

    target_value: Decimal = Field(
        gt=0,
        max_digits=30,
        decimal_places=10
    )


class RegisterPushTokenRequest(BaseModel):

    token: str = Field(
        min_length=10,
        max_length=500
    )

    platform: str = Field(
        default="android",
        max_length=50
    )


# ==================================================
# Create Alert
# ==================================================

@router.post("")
def create_new_alert(
    data: CreateAlertRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    symbol = data.symbol.strip().upper()

    alert_type = (
        data.alert_type.strip().upper()
    )

    if alert_type not in ALERT_TYPES:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid alert type. "
                "Allowed: "
                "PRICE_ABOVE, PRICE_BELOW, "
                "CHANGE_24H_ABOVE, "
                "CHANGE_24H_BELOW"
            )
        )

    asset = db.execute(
        select(Asset)
        .where(
            Asset.symbol == symbol,
            Asset.is_active.is_(True)
        )
    ).scalar_one_or_none()

    if not asset:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    try:

        alert = create_alert(
            db,
            current_user,
            asset,
            alert_type,
            Decimal(
                str(data.target_value)
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    return {
        "message": "Alert created successfully",
        "data": {
            "id": alert.id,
            "symbol": asset.symbol,
            "name": asset.name,
            "alert_type": alert.alert_type,
            "target_value": alert.target_value,
            "is_active": alert.is_active,
            "is_triggered": alert.is_triggered,
            "created_at": alert.created_at
        }
    }


# ==================================================
# FCM Push Token
# ==================================================

@router.post("/notifications/register-token")
def register_notification_token(
    data: RegisterPushTokenRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    try:

        push_token = register_push_token(
            db=db,
            user=current_user,
            token=data.token,
            platform=data.platform
        )

    except ValueError as error:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    return {
        "message": "Push token registered successfully",
        "data": {
            "id": push_token.id,
            "platform": push_token.platform
        }
    }


@router.delete("/notifications/remove-token")
def remove_notification_token(
    data: RegisterPushTokenRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    removed = remove_push_token(
        db=db,
        user=current_user,
        token=data.token
    )

    if not removed:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push token not found"
        )

    return {
        "message": "Push token removed successfully"
    }


# ==================================================
# Notification Setup
# ==================================================

@router.get("/notifications/setup")
def notification_setup(
    current_user: User = Depends(
        get_current_user
    )
):

    topic = get_user_topic(
        current_user.id
    )

    return {
        "enabled": True,
        "provider": "ntfy",
        "topic": topic,
        "subscribe_url": get_user_topic_url(
            current_user.id
        ),
        "message": (
            "Subscribe to this topic in ntfy "
            "to receive Rasad alerts."
        ),
    }


# ==================================================
# Notification Test
# ==================================================

@router.post("/notifications/test")
def test_notification(
    current_user: User = Depends(
        get_current_user
    )
):

    sent = send_ntfy_notification(
        user_id=current_user.id,
        title="🔔 تست اعلان رصد",
        message=(
            "اگر این پیام را دریافت کردی، "
            "اتصال اعلان‌های رصد به ntfy درست است."
        ),
        priority="high",
        tags=["bell", "test_tube"],
    )

    if not sent:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send notification through ntfy"
        )

    return {
        "message": "Test notification sent successfully"
    }


# ==================================================
# List User Alerts
# ==================================================

@router.get("")
def list_alerts(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    rows = get_user_alerts(
        db,
        current_user
    )

    return {
        "count": len(rows),
        "data": [

            {
                "id": alert.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "alert_type": alert.alert_type,
                "target_value": alert.target_value,
                "is_active": alert.is_active,
                "is_triggered": alert.is_triggered,
                "triggered_at": alert.triggered_at,
                "triggered_value": alert.triggered_value,
                "triggered_price": alert.triggered_price,
                "notification_sent_at": (
                    alert.notification_sent_at
                ),
                "created_at": alert.created_at
            }

            for alert, asset in rows
        ]
    }


# ==================================================
# Get Notifications
# ==================================================

@router.get("/notifications")
def get_notifications(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    rows = get_unnotified_triggered_alerts(
        db,
        current_user
    )

    return {
        "count": len(rows),
        "data": [

            {
                "id": alert.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "alert_type": alert.alert_type,
                "target_value": alert.target_value,
                "triggered_at": alert.triggered_at,
                "triggered_value": alert.triggered_value,
                "triggered_price": alert.triggered_price
            }

            for alert, asset in rows
        ]
    }


# ==================================================
# Mark Notification As Sent
# ==================================================

@router.post("/{alert_id}/notification-sent")
def notification_sent(
    alert_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    alert = mark_notification_sent(
        db,
        current_user,
        alert_id
    )

    if not alert:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return {
        "message": "Notification marked as sent",
        "alert_id": alert.id,
        "notification_sent_at":
            alert.notification_sent_at
    }


# ==================================================
# Deactivate Alert
# ==================================================

@router.patch("/{alert_id}/deactivate")
def deactivate(
    alert_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    alert = deactivate_alert(
        db,
        current_user,
        alert_id
    )

    if not alert:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return {
        "message": "Alert deactivated",
        "alert_id": alert.id,
        "is_active": alert.is_active
    }


# ==================================================
# Delete Alert
# ==================================================

@router.delete("/{alert_id}")
def remove_alert(
    alert_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    deleted = delete_alert(
        db,
        current_user,
        alert_id
    )

    if not deleted:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    return {
        "message": "Alert deleted successfully",
        "alert_id": alert_id
    }


# ==================================================
# Development Test Trigger
# ==================================================