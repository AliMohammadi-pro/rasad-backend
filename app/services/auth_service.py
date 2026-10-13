from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

from app.utils.security import (
    hash_password,
    verify_password
)


# ==========================================
# Get User By Email
# ==========================================

def get_user_by_email(
    db: Session,
    email: str
) -> User | None:

    result = db.execute(
        select(User).where(
            User.email == email
        )
    )

    return result.scalar_one_or_none()


# ==========================================
# Create User
# ==========================================

def create_user(
    db: Session,
    email: str,
    password: str
) -> User:

    password_hash = hash_password(
        password
    )

    user = User(
        email=email,
        password_hash=password_hash,
        is_verified=False,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ==========================================
# Authenticate User
# ==========================================

def authenticate_user(
    db: Session,
    email: str,
    password: str
) -> User | None:

    user = get_user_by_email(
        db,
        email
    )

    if not user:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user


# ==========================================
# Change Password
# ==========================================

def reset_user_password(
    db: Session,
    user: User,
    new_password: str
) -> User:

    user.password_hash = hash_password(
        new_password
    )

    db.commit()
    db.refresh(user)

    return user