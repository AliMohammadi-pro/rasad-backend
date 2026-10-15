import hashlib
import json
import os
import urllib.error
import urllib.request

from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

from sqlalchemy import select

from app.database import SessionLocal
from app.models.push_token import PushToken


load_dotenv()


# ==================================================
# Firebase
# ==================================================

FIREBASE_CREDENTIALS_PATH = os.getenv(
    "FIREBASE_CREDENTIALS_PATH",
    "./firebase-service-account.json"
)


def _get_firebase_credentials_path() -> Path:
    path = Path(
        FIREBASE_CREDENTIALS_PATH
    )

    if path.is_absolute():
        return path

    backend_dir = Path(__file__).resolve().parents[2]

    return backend_dir / path


def _initialize_firebase():
    """
    Firebase Admin SDK را فقط یک بار initialize می‌کند.

    روی هاست می‌توان کل JSON سرویس‌اکانت را در متغیر
    FIREBASE_SERVICE_ACCOUNT_JSON قرار داد؛ در غیر این صورت
    فایل مسیر FIREBASE_CREDENTIALS_PATH خوانده می‌شود.
    """

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    service_account_json = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        ""
    ).strip()

    if service_account_json:
        try:
            service_account_data = json.loads(
                service_account_json
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON"
            ) from error

        cred = credentials.Certificate(
            service_account_data
        )
    else:
        credentials_path = _get_firebase_credentials_path()

        if not credentials_path.exists():
            raise FileNotFoundError(
                "Firebase service account is not configured. "
                "Set FIREBASE_SERVICE_ACCOUNT_JSON on the host "
                "or provide FIREBASE_CREDENTIALS_PATH."
            )

        cred = credentials.Certificate(
            str(credentials_path)
        )

    return firebase_admin.initialize_app(cred)


# ==================================================
# FCM
# ==================================================

def get_user_push_token_count(user_id: int) -> int:
    """تعداد دستگاه‌های دارای توکن ثبت‌شده برای یک کاربر."""
    db = SessionLocal()
    try:
        return len(db.execute(
            select(PushToken).where(PushToken.user_id == user_id)
        ).scalars().all())
    finally:
        db.close()


def send_fcm_notification(
    user_id: int,
    title: str,
    message: str,
    *,
    priority: str = "high",
    data: dict[str, str] | None = None,
) -> bool:
    """
    ارسال Push Notification از طریق Firebase FCM
    به تمام دستگاه‌های ثبت‌شده کاربر.
    """

    db = SessionLocal()

    try:

        _initialize_firebase()

        result = db.execute(
            select(PushToken)
            .where(
                PushToken.user_id == user_id
            )
        )

        push_tokens = result.scalars().all()

        if not push_tokens:
            print(
                f"[FCM] No push tokens found for user {user_id}"
            )
            return False

        sent_count = 0

        for push_token in push_tokens:

            notification = messaging.Notification(
                title=title,
                body=message
            )

            android_config = messaging.AndroidConfig(
                priority=priority
            )

            fcm_message = messaging.Message(
                notification=notification,
                android=android_config,
                token=push_token.token,
                data=data or {}
            )

            try:

                response = messaging.send(
                    fcm_message
                )

                print(
                    "[FCM] Notification sent: "
                    f"user={user_id}, "
                    f"token_id={push_token.id}, "
                    f"message_id={response}"
                )

                sent_count += 1

            except messaging.UnregisteredError:

                print(
                    "[FCM] Removing invalid token: "
                    f"{push_token.id}"
                )

                db.delete(push_token)

            except messaging.SenderIdMismatchError as error:

                print(
                    "[FCM] Sender ID mismatch: "
                    f"{error}"
                )

            except Exception as error:

                print(
                    "[FCM] Token send failed "
                    f"(token_id={push_token.id}): "
                    f"{error}"
                )

        db.commit()

        return sent_count > 0

    except Exception as error:

        db.rollback()

        print(
            f"[FCM] Notification failed: {error}"
        )

        return False

    finally:

        db.close()


# ==================================================
# NTFY - Temporary Compatibility
# ==================================================

NTFY_BASE_URL = os.getenv(
    "NTFY_BASE_URL",
    "https://ntfy.sh",
).rstrip("/")


NTFY_TOPIC_PREFIX = os.getenv(
    "NTFY_TOPIC_PREFIX",
    "rasad-alert",
).strip().strip("/")


NTFY_TOPIC_SALT = (
    os.getenv("NTFY_TOPIC_SALT")
    or os.getenv("SECRET_KEY", "")
)


REQUEST_TIMEOUT = 10


def get_user_topic(
    user_id: int
) -> str:

    if not NTFY_TOPIC_SALT:

        raise RuntimeError(
            "NTFY_TOPIC_SALT is not configured"
        )

    digest = hashlib.sha256(
        f"{NTFY_TOPIC_SALT}:user:{user_id}".encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        f"{NTFY_TOPIC_PREFIX}-"
        f"{digest[:32]}"
    )


def get_user_topic_url(
    user_id: int
) -> str:

    return (
        f"{NTFY_BASE_URL}/"
        f"{get_user_topic(user_id)}"
    )


def _priority_value(
    priority: str | int
) -> str:

    if isinstance(priority, int):

        priority_map = {
            1: "min",
            2: "low",
            3: "default",
            4: "high",
            5: "max",
        }

        return priority_map.get(
            priority,
            "default"
        )

    return str(priority)


def send_ntfy_notification(
    user_id: int,
    title: str,
    message: str,
    *,
    priority: str | int = "high",
    tags: list[str] | None = None,
    click_url: str | None = None,
) -> bool:

    topic = get_user_topic(
        user_id
    )

    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "priority": _priority_value(
            priority
        ),
    }

    if tags:
        payload["tags"] = tags

    if click_url:
        payload["click"] = click_url

    body = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{NTFY_BASE_URL}/",
        data=body,
        headers={
            "Content-Type":
                "application/json; charset=utf-8",
            "Accept":
                "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:

            status = getattr(
                response,
                "status",
                200
            )

            response_body = response.read().decode(
                "utf-8",
                errors="replace",
            )

        if not (
            200 <= status < 300
        ):

            print(
                f"[NTFY] HTTP {status}: "
                f"{response_body[:500]}"
            )

            return False

        return True

    except urllib.error.HTTPError as error:

        body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        print(
            f"[NTFY] HTTP error "
            f"{error.code}: "
            f"{body[:500]}"
        )

        return False

    except urllib.error.URLError as error:

        print(
            f"[NTFY] Network error: {error}"
        )

        return False

    except Exception as error:

        print(
            f"[NTFY] Unexpected error: {error}"
        )

        return False


# ==================================================
# Alert Notification Text
# ==================================================

def build_alert_notification(
    symbol: str,
    name: str | None,
    alert_type: str,
    target_value: Decimal,
    triggered_value: Decimal,
) -> tuple[str, str]:

    type_text = {
        "PRICE_ABOVE":
            "قیمت بالاتر از حد تعیین‌شده",

        "PRICE_BELOW":
            "قیمت پایین‌تر از حد تعیین‌شده",

        "CHANGE_24H_ABOVE":
            "تغییرات ۲۴ ساعته بالاتر از حد تعیین‌شده",

        "CHANGE_24H_BELOW":
            "تغییرات ۲۴ ساعته پایین‌تر از حد تعیین‌شده",

    }.get(
        alert_type,
        "هشدار بازار"
    )

    title = (
        f"🔔 هشدار {symbol}"
    )

    message = (
        f"{name or symbol}\n"
        f"{type_text}\n"
        f"حد هشدار: {target_value}\n"
        f"مقدار فعلی: {triggered_value}"
    )

    return title, message