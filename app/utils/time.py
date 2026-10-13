from datetime import datetime, timezone
from zoneinfo import ZoneInfo


TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def utc_now() -> datetime:
    """
    زمان فعلی UTC
    """
    return datetime.now(timezone.utc)


def tehran_now() -> datetime:
    """
    زمان فعلی ایران
    """
    return datetime.now(TEHRAN_TZ)


def tehran_today_start_utc() -> datetime:
    """
    شروع روز جاری ایران، تبدیل‌شده به UTC
    برای استفاده در Query های دیتابیس
    """
    now_tehran = tehran_now()

    start_of_day_tehran = now_tehran.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    return start_of_day_tehran.astimezone(
        timezone.utc
    )