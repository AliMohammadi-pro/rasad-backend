from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.push_token import PushToken
from app.models.user import User


def register_push_token(
    db: Session,
    user: User,
    token: str,
    platform: str = "android"
) -> PushToken:

    token = token.strip()
    platform = (platform or "android").strip()[:50] or "android"

    if not token:
        raise ValueError("FCM token cannot be empty")

    # FCM tokens are globally unique. If this device was previously
    # used by another account, attach the token to the current account.
    result = db.execute(
        select(PushToken).where(
            PushToken.token == token
        )
    )
    push_token = result.scalar_one_or_none()

    if push_token:
        push_token.user_id = user.id
        push_token.platform = platform
        push_token.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(push_token)
        return push_token

    push_token = PushToken(
        user_id=user.id,
        token=token,
        platform=platform
    )

    db.add(push_token)
    db.commit()
    db.refresh(push_token)
    return push_token


def remove_push_token(
    db: Session,
    user: User,
    token: str
) -> bool:

    result = db.execute(
        select(PushToken)
        .where(
            PushToken.user_id == user.id,
            PushToken.token == token
        )
    )

    push_token = result.scalar_one_or_none()

    if not push_token:
        return False

    db.delete(push_token)
    db.commit()

    return True