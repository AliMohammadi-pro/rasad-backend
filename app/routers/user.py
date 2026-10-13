from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/user",
    tags=["User"]
)


@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }