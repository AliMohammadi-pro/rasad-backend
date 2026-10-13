import os

from datetime import (
    datetime,
    timedelta,
    timezone
)

import bcrypt

from dotenv import load_dotenv

from jose import jwt


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY is not set"
    )


ALGORITHM = "HS256"


# =========================================================
# Token Expiration
# =========================================================

ACCESS_TOKEN_EXPIRE_MINUTES = 60

REFRESH_TOKEN_EXPIRE_DAYS = 30


# =========================================================
# Password
# =========================================================

def hash_password(
    password: str
) -> str:

    password_bytes = password.encode(
        "utf-8"
    )

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode(
        "utf-8"
    )


def verify_password(
    password: str,
    password_hash: str
) -> bool:

    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )


# =========================================================
# Access Token
# =========================================================

def create_access_token(
    user_id: int
) -> str:

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# Refresh Token
# =========================================================

def create_refresh_token(
    user_id: int
) -> str:

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )