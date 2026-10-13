import hashlib
import secrets

from datetime import (
    datetime,
    timedelta
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_verification import (
    EmailVerification
)

from app.models.user import User


TOKEN_EXPIRE_MINUTES = 30


# ==========================================
# Generate Verification Token
# ==========================================

def generate_verification_token(
    db: Session,
    user: User
) -> str:

    old_tokens = db.execute(
        select(EmailVerification).where(
            EmailVerification.user_id == user.id,
            EmailVerification.used_at.is_(None)
        )
    ).scalars().all()

    for old_token in old_tokens:
        old_token.used_at = datetime.utcnow()

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    verification = EmailVerification(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=(
            datetime.utcnow()
            + timedelta(
                minutes=TOKEN_EXPIRE_MINUTES
            )
        )
    )

    db.add(verification)
    db.commit()

    return raw_token


# ==========================================
# Verify Email Token
# ==========================================

def verify_email_token(
    db: Session,
    raw_token: str
) -> User | None:

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    result = db.execute(
        select(EmailVerification).where(
            EmailVerification.token_hash
            == token_hash
        )
    )

    verification = (
        result.scalar_one_or_none()
    )

    if not verification:
        return None

    if verification.used_at is not None:
        return None

    if verification.expires_at < datetime.utcnow():
        return None

    user = db.get(
        User,
        verification.user_id
    )

    if not user:
        return None

    user.is_verified = True

    verification.used_at = (
        datetime.utcnow()
    )

    db.commit()
    db.refresh(user)

    return user