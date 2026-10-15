import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["User"])


def is_admin_email(email: str) -> bool:
    configured = os.getenv("FEEDBACK_ADMIN_EMAIL", "").strip().lower()
    return bool(configured) and email.strip().lower() == configured


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "is_admin": is_admin_email(current_user.email),
        "created_at": current_user.created_at,
    }


@router.get("/admin/users")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not os.getenv("FEEDBACK_ADMIN_EMAIL", "").strip():
        raise HTTPException(status_code=503, detail="متغیر FEEDBACK_ADMIN_EMAIL در سرور تنظیم نشده است.")
    if not is_admin_email(current_user.email):
        raise HTTPException(status_code=403, detail="فقط مدیر اجازه مشاهده فهرست کاربران را دارد.")
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return [{
        "id": user.id,
        "email": user.email,
        "is_verified": user.is_verified,
        "is_active": user.is_active,
        "created_at": user.created_at,
    } for user in users]
