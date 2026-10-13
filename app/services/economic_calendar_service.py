import json
import urllib.error
import urllib.parse
import urllib.request

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.economic_calendar import EconomicCalendar


BIQUOTE_CALENDAR_URL = "https://biquote.io/api/calendar"

REQUEST_TIMEOUT = 20


# =========================================================
# کشورهای مهم اقتصادی
# =========================================================

IMPORTANT_COUNTRIES = [
    {
        "code": "US",
        "name": "United States",
        "name_fa": "آمریکا",
        "flag": "🇺🇸",
    },
    {
        "code": "EU",
        "name": "Eurozone",
        "name_fa": "منطقه یورو",
        "flag": "🇪🇺",
    },
    {
        "code": "GB",
        "name": "United Kingdom",
        "name_fa": "بریتانیا",
        "flag": "🇬🇧",
    },
    {
        "code": "JP",
        "name": "Japan",
        "name_fa": "ژاپن",
        "flag": "🇯🇵",
    },
    {
        "code": "CN",
        "name": "China",
        "name_fa": "چین",
        "flag": "🇨🇳",
    },
    {
        "code": "CA",
        "name": "Canada",
        "name_fa": "کانادا",
        "flag": "🇨🇦",
    },
    {
        "code": "AU",
        "name": "Australia",
        "name_fa": "استرالیا",
        "flag": "🇦🇺",
    },
    {
        "code": "CH",
        "name": "Switzerland",
        "name_fa": "سوئیس",
        "flag": "🇨🇭",
    },
    {
        "code": "NZ",
        "name": "New Zealand",
        "name_fa": "نیوزیلند",
        "flag": "🇳🇿",
    },
    {
        "code": "DE",
        "name": "Germany",
        "name_fa": "آلمان",
        "flag": "🇩🇪",
    },
]

IMPORTANT_COUNTRY_CODES = {
    item["code"]
    for item in IMPORTANT_COUNTRIES
}


# =========================================================
# Helpers
# =========================================================

def _parse_datetime(value):

    if not value:
        return None

    text = str(value).strip()

    try:

        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        if parsed.tzinfo is not None:
            parsed = (
                parsed
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return parsed

    except ValueError:
        return None


def _value_to_string(value):

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
        )

    return str(value)


def _normalise_country(event):

    value = (
        event.get("countryCode")
        or event.get("country")
    )

    if not value:
        return None

    return str(value).strip().upper()


def _parse_country_filter(country):

    if not country:
        return set(IMPORTANT_COUNTRY_CODES)

    country = country.strip().upper()

    if country == "ALL":
        return set(IMPORTANT_COUNTRY_CODES)

    result = set()

    for item in country.split(","):

        code = item.strip().upper()

        if code in IMPORTANT_COUNTRY_CODES:
            result.add(code)

    return result


# =========================================================
# دریافت اطلاعات از BiQuote
# =========================================================

def _fetch_calendar(params):

    query = urllib.parse.urlencode(params)

    url = f"{BIQUOTE_CALENDAR_URL}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Rasad/1.0",
        },
        method="GET",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"BiQuote HTTP {exc.code}: {body[:500]}"
        ) from exc

    except urllib.error.URLError as exc:

        raise RuntimeError(
            f"BiQuote network error: {exc}"
        ) from exc

    try:

        payload = json.loads(body)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "BiQuote returned invalid JSON"
        ) from exc

    if not isinstance(payload, list):

        raise RuntimeError(
            "BiQuote calendar response is not a list"
        )

    return payload


# =========================================================
# Countries
# =========================================================

def get_important_countries():

    return IMPORTANT_COUNTRIES


# =========================================================
# Refresh
# =========================================================

def refresh_economic_calendar(
    db: Session,
    days: int = 30,
    country: str = "ALL",
    importance: str | None = "medium",
):

    days = max(
        1,
        min(days, 90),
    )

    selected_countries = _parse_country_filter(
        country
    )

    if not selected_countries:

        raise ValueError(
            "No valid economic calendar country selected."
        )

    start = (
        date.today()
        - timedelta(days=1)
    )

    end = (
        date.today()
        + timedelta(days=days)
    )

    countries_param = ",".join(
        sorted(selected_countries)
    )

    params = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "countries": countries_param,
        "limit": 500,
    }

    if importance:

        importance_value = (
            importance.lower().strip()
        )

        if importance_value in (
            "medium",
            "high",
        ):
            params["importance"] = (
                importance_value
            )

    events = _fetch_calendar(params)

    saved = 0
    updated = 0
    skipped = 0

    for event in events:

        if not isinstance(event, dict):
            skipped += 1
            continue

        release_id = (
            event.get("id")
            or event.get("releaseId")
            or event.get("eventId")
        )

        name = (
            event.get("name")
            or event.get("title")
        )

        # -------------------------------------------------
        # زمان
        # -------------------------------------------------

        scheduled_at = _parse_datetime(
            event.get("time")
            or event.get("scheduled_at")
            or event.get("scheduledAt")
        )

        if not release_id or not name:

            skipped += 1
            continue

        # -------------------------------------------------
        # کشور
        # -------------------------------------------------

        country_code = _normalise_country(
            event
        )

        if not country_code:

            skipped += 1
            continue

        if country_code not in selected_countries:

            skipped += 1
            continue

        # -------------------------------------------------
        # اهمیت
        # -------------------------------------------------

        event_importance = str(
            event.get("importance")
            or "medium"
        ).lower()

        if importance:

            importance_value = (
                importance.lower().strip()
            )

            if (
                importance_value == "high"
                and event_importance != "high"
            ):
                continue

            if (
                importance_value == "medium"
                and event_importance
                not in (
                    "medium",
                    "high",
                )
            ):
                continue

        # -------------------------------------------------
        # تاریخ
        # -------------------------------------------------

        period = event.get("period")

        if scheduled_at:

            event_date = scheduled_at.date()

        elif period:

            try:

                event_date = date.fromisoformat(
                    str(period)[:10]
                )

            except ValueError:

                event_date = date.today()

        else:

            event_date = date.today()

        # -------------------------------------------------
        # مقادیر اقتصادی
        # -------------------------------------------------

        actual = event.get("actual")

        forecast = event.get("forecast")

        previous = event.get("previous")

        revised_previous = (
            event.get("revisedPrevious")
            or event.get("revised_previous")
        )

        # -------------------------------------------------
        # وضعیت
        # -------------------------------------------------

        # بسیار مهم:
        # actual اگر None باشد یعنی هنوز اعلام نشده
        # اگر مقدار داشته باشد یعنی اعلام شده

        status = (
            "released"
            if actual is not None
            else "upcoming"
        )

        values = {

            "release_name": str(name),

            "scheduled_at": scheduled_at,

            "country": country_code,

            "currency": _value_to_string(
                event.get("currency")
            ),

            "importance":
                event_importance,

            "event_type":
                _value_to_string(
                    event.get("type")
                ),

            "sector":
                _value_to_string(
                    event.get("sector")
                ),

            "unit":
                _value_to_string(
                    event.get("unit")
                ),

            "multiplier":
                _value_to_string(
                    event.get("multiplier")
                ),

            "status":
                status,

            "previous_value":
                _value_to_string(
                    previous
                ),

            "forecast_value":
                _value_to_string(
                    forecast
                ),

            "actual_value":
                _value_to_string(
                    actual
                ),

            "revised_previous_value":
                _value_to_string(
                    revised_previous
                ),

            "source":
                _value_to_string(
                    event.get("source")
                )
                or "biquote",

            "source_url":
                _value_to_string(
                    event.get("sourceUrl")
                ),

            "updated_at":
                datetime.utcnow(),
        }

        # -------------------------------------------------
        # پیدا کردن رویداد موجود
        # -------------------------------------------------

        existing = db.scalar(
            select(EconomicCalendar)
            .where(
                EconomicCalendar.release_id
                == str(release_id),

                EconomicCalendar.event_date
                == event_date,
            )
        )

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        if existing:

            for key, value in values.items():

                setattr(
                    existing,
                    key,
                    value,
                )

            updated += 1

        # -------------------------------------------------
        # INSERT
        # -------------------------------------------------

        else:

            db.add(
                EconomicCalendar(
                    release_id=str(release_id),
                    event_date=event_date,
                    **values,
                )
            )

            saved += 1

    db.commit()

    return {
        "received": len(events),
        "saved": saved,
        "updated": updated,
        "skipped": skipped,
        "countries": sorted(
            selected_countries
        ),
        "country": country.upper(),
        "from": start.isoformat(),
        "to": end.isoformat(),
        "source": "biquote",
    }