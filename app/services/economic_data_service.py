import json
import os
import urllib.parse
import urllib.request

from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.economic_indicator import (
    EconomicIndicator
)


load_dotenv()

ALPHA_VANTAGE_URL = (
    "https://www.alphavantage.co/query"
)

ALPHA_VANTAGE_API_KEY = os.getenv(
    "ALPHA_VANTAGE_API_KEY"
)

REQUEST_TIMEOUT = 20


SUPPORTED_INDICATORS = {

    "CPI": {
        "interval": "monthly",
        "unit": "index"
    },

    "NONFARM_PAYROLL": {
        "interval": "monthly",
        "unit": "thousand_jobs"
    },

    "UNEMPLOYMENT": {
        "interval": "monthly",
        "unit": "percent"
    },

    "REAL_GDP": {
        "interval": "quarterly",
        "unit": "percent"
    },

    "FEDERAL_FUNDS_RATE": {
        "interval": "monthly",
        "unit": "percent"
    },

    "RETAIL_SALES": {
        "interval": "monthly",
        "unit": "million_usd"
    },

    "DURABLES": {
        "interval": "monthly",
        "unit": "million_usd"
    },

    "INFLATION": {
        "interval": None,
        "unit": "percent"
    },

    "CONSUMER_SENTIMENT": {
        "interval": "monthly",
        "unit": "index"
    },
}


def _request(
    indicator: str
) -> dict:

    config = SUPPORTED_INDICATORS.get(
        indicator
    )

    if not config:
        raise RuntimeError(
            f"Unsupported economic indicator: {indicator}"
        )

    params = {
        "function": indicator,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    if config["interval"]:
        params["interval"] = config["interval"]

    url = (
        f"{ALPHA_VANTAGE_URL}?"
        f"{urllib.parse.urlencode(params)}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CryptoMarket/1.0",
            "Accept": "application/json",
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as error:

        raise RuntimeError(
            f"Economic API request failed: {error}"
        )


def fetch_indicator(
    indicator: str
) -> list[dict]:

    if not ALPHA_VANTAGE_API_KEY:

        raise RuntimeError(
            "ALPHA_VANTAGE_API_KEY is not set."
        )

    indicator = indicator.upper()

    data = _request(
        indicator
    )

    if "Error Message" in data:

        raise RuntimeError(
            data["Error Message"]
        )

    if "Information" in data:

        raise RuntimeError(
            data["Information"]
        )

    return data.get(
        "data",
        []
    )


def save_indicator(
    db: Session,
    indicator: str,
    rows: list[dict]
) -> int:

    config = SUPPORTED_INDICATORS[
        indicator
    ]

    saved = 0

    for row in rows:

        date = row.get(
            "date"
        )

        value = row.get(
            "value"
        )

        if not date or value in (
            None,
            "",
            "None"
        ):
            continue

        try:
            numeric_value = float(value)
        except (
            TypeError,
            ValueError
        ):
            continue

        existing = db.execute(
            select(
                EconomicIndicator
            ).where(
                EconomicIndicator.indicator
                == indicator,
                EconomicIndicator.date
                == date
            )
        ).scalar_one_or_none()

        if existing:

            existing.value = numeric_value
            existing.unit = config["unit"]

            continue

        db.add(
            EconomicIndicator(
                indicator=indicator,
                date=date,
                value=numeric_value,
                unit=config["unit"],
                source="Alpha Vantage"
            )
        )

        saved += 1

    db.commit()

    return saved