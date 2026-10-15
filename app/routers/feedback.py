import os
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.utils.auth import get_current_user
from app.utils.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])
optional_bearer = HTTPBearer(auto_error=False)
FeedbackName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
FeedbackMessage = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]


class FeedbackCreate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    rating: int = Field(ge=1, le=5)
    message: FeedbackMessage


class FeedbackItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str | None
    email: str | None = None
    rating: int
    message: str
    is_approved: bool = False
    created_at: datetime


class FeedbackStats(BaseModel):
    average_rating: float
    approved_count: int


_recent_submissions: dict[str, deque[float]] = defaultdict(deque)
RATE_WINDOW_SECONDS = 3600
MAX_SUBMISSIONS_PER_WINDOW = 5


def _admin_email() -> str:
    return os.getenv("FEEDBACK_ADMIN_EMAIL", "").strip().lower()


def require_feedback_admin(current_user: User = Depends(get_current_user)) -> User:
    admin_email = _admin_email()
    if not admin_email:
        raise HTTPException(status_code=503, detail="متغیر FEEDBACK_ADMIN_EMAIL در تنظیمات سرور مشخص نشده است.")
    if current_user.email.strip().lower() != admin_email:
        raise HTTPException(status_code=403, detail="شما اجازه مدیریت نظرات و کاربران را ندارید.")
    return current_user


def optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        raw_id = payload.get("sub")
        user_id = int(raw_id)
    except (JWTError, TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    if not user or not user.is_active or not user.is_verified:
        return None
    return user


@router.get("/public")
def public_feedback(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Feedback).where(Feedback.is_approved.is_(True)).order_by(Feedback.created_at.desc(), Feedback.id.desc()).limit(100)
    ).all()
    avg, count = db.query(func.avg(Feedback.rating), func.count(Feedback.id)).filter(Feedback.is_approved.is_(True)).one()
    return {
        "items": [FeedbackItem.model_validate(row) for row in rows],
        "average_rating": round(float(avg or 0), 2),
        "approved_count": int(count or 0),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(optional_current_user),
):
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "unknown")
    now = time.monotonic()
    submissions = _recent_submissions[client_ip]
    while submissions and now - submissions[0] > RATE_WINDOW_SECONDS:
        submissions.popleft()
    if len(submissions) >= MAX_SUBMISSIONS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="تعداد ارسال نظر در یک ساعت بیش از حد مجاز است.")

    guest_name = (payload.name or "").strip() or None
    if current_user is None and not guest_name:
        raise HTTPException(status_code=400, detail="برای ثبت نظر به‌عنوان مهمان، نام خود را وارد کنید.")

    feedback = Feedback(
        name=None if current_user else guest_name,
        email=current_user.email if current_user else None,
        user_id=current_user.id if current_user else None,
        rating=payload.rating,
        message=payload.message.strip(),
        is_approved=False,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    submissions.append(now)
    return {"id": feedback.id, "message": "نظر شما ثبت شد و پس از تأیید مدیر نمایش داده می‌شود."}


@router.get("/admin", response_model=list[FeedbackItem])
def list_feedback(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_feedback_admin),
):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    return list(db.scalars(select(Feedback).order_by(Feedback.created_at.desc(), Feedback.id.desc()).offset(offset).limit(limit)).all())


@router.patch("/{feedback_id}/approve")
def approve_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_feedback_admin),
):
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="نظر پیدا نشد.")
    feedback.is_approved = not feedback.is_approved
    db.commit()
    return {"id": feedback.id, "is_approved": feedback.is_approved}


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), _: User = Depends(require_feedback_admin)):
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="نظر پیدا نشد.")
    db.delete(feedback)
    db.commit()
    return None
