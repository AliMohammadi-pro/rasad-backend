import hashlib
import secrets

from datetime import (
    datetime,
    timedelta
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from fastapi.responses import HTMLResponse
from urllib.parse import quote

from jose import (
    JWTError,
    jwt
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.password_reset import (
    PasswordReset
)

from app.models.user import User

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    VerifyEmailResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)

from app.services.auth_service import (
    get_user_by_email,
    create_user,
    authenticate_user,
    reset_user_password
)

from app.services.email_verification_service import (
    generate_verification_token,
    verify_email_token
)

from app.services.email_service import (
    send_verification_email,
    send_password_reset_email
)

from app.utils.security import (
    create_access_token,
    create_refresh_token,
    SECRET_KEY,
    ALGORITHM
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


PASSWORD_RESET_EXPIRE_MINUTES = 30


# ==========================================
# Register
# ==========================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    email = data.email.lower()

    existing_user = get_user_by_email(
        db,
        email
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    user = create_user(
        db,
        email,
        data.password
    )

    verification_token = (
        generate_verification_token(
            db,
            user
        )
    )

    send_verification_email(
        user.email,
        verification_token
    )

    return AuthResponse(
        message=(
            "User registered successfully. "
            "Please check your email."
        ),
        user_id=user.id,
        email=user.email
    )


# ==========================================
# Login
# ==========================================

@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    email = data.email.lower()

    user = authenticate_user(
        db,
        email,
        data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ایمیل ویا رمز عبور نادرست است"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب مورد نظر غیرفعال است"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "لطفا قبل از ورود ایمیل خود را تایید کنید"
            )
        )

    # Access Token
    access_token = create_access_token(
        user.id
    )

    # Refresh Token
    refresh_token = create_refresh_token(
        user.id
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )


# ==========================================
# Refresh Access Token
# ==========================================

@router.post(
    "/refresh",
    response_model=RefreshTokenResponse
)
def refresh_access_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):

    try:

        payload = jwt.decode(
            data.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        user_id = int(user_id)

    except HTTPException:
        raise

    except (
        JWTError,
        ValueError,
        TypeError
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user = db.get(
        User,
        user_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not verified"
        )

    new_access_token = create_access_token(
        user.id
    )

    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="bearer"
    )


# ==========================================
# Verify Email
# ==========================================

@router.get(
    "/verify-email",
    response_model=VerifyEmailResponse
)
def verify_email(
    token: str,
    db: Session = Depends(get_db)
):

    user = verify_email_token(
        db,
        token
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "verification token"
            )
        )

    return VerifyEmailResponse(
        message="Email verified successfully",
        user_id=user.id,
        email=user.email,
        is_verified=user.is_verified
    )


# ==========================================
# Open Android App from Verification Email
# ==========================================

@router.get(
    "/open-verification-app",
    response_class=HTMLResponse,
    include_in_schema=False
)
def open_verification_app(token: str):
    """Show a normal HTTP page with a button to open the Rasad Android app."""
    from html import escape
    import json

    encoded_token = quote(token, safe="")
    app_url = f"rasad://verify-email?token={encoded_token}"
    safe_app_url = escape(app_url, quote=True)
    js_app_url = json.dumps(app_url)

    return f"""
    <!doctype html>
    <html lang="fa" dir="rtl">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>تأیید ایمیل رصد</title>
    </head>
    <body style="margin:0;padding:24px;background:#f5f7fb;font-family:Arial,sans-serif;text-align:center;color:#202638">
      <main style="max-width:480px;margin:48px auto;padding:28px 20px;background:#fff;border-radius:16px">
        <h2 style="color:#ff7a18">تأیید ایمیل رصد</h2>
        <p>برای ادامه و تأیید ایمیل، اپلیکیشن رصد را باز کنید.</p>
        <a href="{safe_app_url}" style="display:inline-block;margin:16px 0;padding:14px 24px;background:#ff7a18;color:#fff;text-decoration:none;border-radius:8px">باز کردن اپلیکیشن رصد</a>
        <p style="font-size:13px;color:#667085">اگر اپ باز نشد، مطمئن شوید اپلیکیشن رصد روی گوشی نصب است.</p>
      </main>
      <script>
        // تلاش خودکار ممکن است توسط مرورگر مسدود شود؛ دکمه بالا نیز موجود است.
        window.location.href = {js_app_url};
      </script>
    </body>
    </html>
    """


# ==========================================
# Resend Verification Email
# ==========================================

@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse
)
def resend_verification(
    data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):

    email = data.email.lower()

    user = get_user_by_email(
        db,
        email
    )

    # پاسخ یکسان برای جلوگیری از
    # Email Enumeration

    generic_message = (
        "If the account exists and "
        "is not verified, a new "
        "verification email has been sent."
    )

    if not user:
        return ResendVerificationResponse(
            message=generic_message
        )

    if user.is_verified:
        return ResendVerificationResponse(
            message=generic_message
        )

    if not user.is_active:
        return ResendVerificationResponse(
            message=generic_message
        )

    verification_token = (
        generate_verification_token(
            db,
            user
        )
    )

    send_verification_email(
        user.email,
        verification_token
    )

    return ResendVerificationResponse(
        message=generic_message
    )


# ==========================================
# Forgot Password
# ==========================================

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):

    email = data.email.lower()

    user = get_user_by_email(
        db,
        email
    )

    generic_message = (
        "If an account with this email exists, "
        "a password reset link has been sent."
    )

    # برای جلوگیری از Email Enumeration

    if not user:
        return ForgotPasswordResponse(
            message=generic_message
        )

    if not user.is_active:
        return ForgotPasswordResponse(
            message=generic_message
        )

    # باطل کردن Tokenهای قبلی

    old_resets = db.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user.id,
            PasswordReset.used_at.is_(None)
        )
    ).scalars().all()

    for old_reset in old_resets:
        old_reset.used_at = datetime.utcnow()

    # ساخت Token جدید

    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    password_reset = PasswordReset(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=(
            datetime.utcnow()
            + timedelta(
                minutes=PASSWORD_RESET_EXPIRE_MINUTES
            )
        )
    )

    db.add(password_reset)

    db.commit()

    send_password_reset_email(
        user.email,
        raw_token
    )

    return ForgotPasswordResponse(
        message=generic_message
    )


# ==========================================
# Reset Password
# ==========================================

@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):

    token_hash = hashlib.sha256(
        data.token.encode("utf-8")
    ).hexdigest()

    result = db.execute(
        select(PasswordReset).where(
            PasswordReset.token_hash
            == token_hash
        )
    )

    password_reset = (
        result.scalar_one_or_none()
    )

    if not password_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token"
            )
        )

    if password_reset.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token"
            )
        )

    if password_reset.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token"
            )
        )

    user = db.get(
        User,
        password_reset.user_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token"
            )
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # تغییر رمز عبور

    reset_user_password(
        db,
        user,
        data.new_password
    )

    # مصرف شدن Token

    password_reset.used_at = (
        datetime.utcnow()
    )

    db.commit()

    return ResetPasswordResponse(
        message="Password reset successfully"
    )