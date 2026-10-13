from pydantic import BaseModel, EmailStr, Field


# ==========================================
# Register
# ==========================================

class RegisterRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


# ==========================================
# Login
# ==========================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ==========================================
# Auth Responses
# ==========================================

class AuthResponse(BaseModel):
    message: str
    user_id: int
    email: EmailStr


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: int
    email: EmailStr


# ==========================================
# Refresh Token
# ==========================================

class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str


# ==========================================
# Verify Email
# ==========================================

class VerifyEmailResponse(BaseModel):
    message: str
    user_id: int
    email: EmailStr
    is_verified: bool


# ==========================================
# Resend Verification
# ==========================================

class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str


# ==========================================
# Forgot Password
# ==========================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


# ==========================================
# Reset Password
# ==========================================

class ResetPasswordRequest(BaseModel):
    token: str

    new_password: str = Field(
        min_length=8,
        max_length=128
    )


class ResetPasswordResponse(BaseModel):
    message: str