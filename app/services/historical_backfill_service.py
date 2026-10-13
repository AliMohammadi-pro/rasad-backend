from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.market_candle import MarketCandle
from app.services.candle_service import upsert_external_ohlcv_candle
from app.services.market_data_service import COIN_IDS

COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"

# CoinGecko's public historical granularity gives us 5m data for the
# current 1-day window and hourly data for a longer historical window.
FIVE_MINUTE_DAYS = 1
HOURLY_DAYS = 60
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.2
MAX_RETRIES = 2

MINIMUM_5M_CANDLES = 250
MINIMUM_1H_CANDLES = 50
MINIMUM_4H_CANDLES = 50
MINIMUM_1D_CANDLES = 50


def _request_json(url: str) -> dict:
    headers = {
        "User-Agent": "CryptoMarket/1.0",
        "Accept": "application/json",
    }
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code == 429:
                raise RuntimeError("CoinGecko historical rate limit reached.") from error
            if error.code in (500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(2 + attempt * 2)
                continue
            raise RuntimeError(f"CoinGecko HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt < MAX_RETRIES:
                time.sleep(2 + attempt * 2)
                continue
            raise RuntimeError(f"CoinGecko network error: {error}") from error

    raise RuntimeError(f"CoinGecko request failed: {last_error}")


def _fetch_history(symbol: str, days: int, interval: str | None = None) -> list[tuple[datetime, float]]:
    coin_id = COIN_IDS.get(symbol.upper())
    if not coin_id:
        return []

    params = {"vs_currency": "usd", "days": str(days)}
    if interval:
        params["interval"] = interval

    url = COINGECKO_MARKET_CHART_URL.format(coin_id=coin_id)
    url += "?" + urllib.parse.urlencode(params)
    data = _request_json(url)

    points = data.get("prices")
    if not isinstance(points, list):
        return []

    result = []
    for point in points:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            timestamp = datetime.fromtimestamp(
                float(point[0]) / 1000,
                tz=timezone.utc,
            ).replace(tzinfo=None)
            price = float(point[1])
        except (TypeError, ValueError, OverflowError):
            continue
        if price > 0:
            result.append((timestamp, price))

    return result


def _floor_time(timestamp: datetime, minutes: int) -> datetime:
    timestamp = timestamp.replace(second=0, microsecond=0)
    bucket_minute = (timestamp.minute // minutes) * minutes
    return timestamp.replace(minute=bucket_minute)


def _build_candles(
    points: list[tuple[datetime, float]],
    interval_minutes: int,
) -> list[dict]:
    buckets: dict[datetime, list[float]] = defaultdict(list)

    for timestamp, price in points:
        buckets[_floor_time(timestamp, interval_minutes)].append(price)

    candles = []
    for timestamp in sorted(buckets):
        values = buckets[timestamp]
        if not values:
            continue
        candles.append({
            "timestamp": timestamp,
            "open": values[0],
            "high": max(values),
            "low": min(values),
            "close": values[-1],
            # CoinGecko market_chart does not provide true candle volume here.
            "volume": None,
        })
    return candles


def _save_candles(db: Session, asset: Asset, candles: list[dict], interval_minutes: int) -> int:
    saved = 0
    for candle in candles:
        upsert_external_ohlcv_candle(
            db=db,
            asset=asset,
            recorded_at=candle["timestamp"],
            open_price=candle["open"],
            high_price=candle["high"],
            low_price=candle["low"],
            close_price=candle["close"],
            volume=candle.get("volume"),
            interval_minutes=interval_minutes,
        )
        saved += 1
    db.commit()
    return saved


def _count_interval(db: Session, asset: Asset, interval_minutes: int) -> int:
    return len(
        db.execute(
            select(MarketCandle.id)
            .where(
                MarketCandle.asset_id == asset.id,
                MarketCandle.interval_minutes == interval_minutes,
            )
        ).all()
    )


def _has_enough(db: Session, asset: Asset, interval_minutes: int, minimum: int) -> bool:
    return _count_interval(db, asset, interval_minutes) >= minimum


def _aggregate_existing(
    db: Session,
    asset: Asset,
    source_interval: int,
    target_interval: int,
) -> int:
    rows = db.execute(
        select(MarketCandle)
        .where(
            MarketCandle.asset_id == asset.id,
            MarketCandle.interval_minutes == source_interval,
        )
        .order_by(MarketCandle.recorded_at.asc())
    ).scalars().all()

    if not rows:
        return 0

    buckets: dict[datetime, list[MarketCandle]] = defaultdict(list)
    for row in rows:
        bucket = _floor_time(row.recorded_at, target_interval)
        buckets[bucket].append(row)

    candles = []
    for timestamp in sorted(buckets):
        values = buckets[timestamp]
        candles.append({
            "timestamp": timestamp,
            "open": float(values[0].open),
            "high": max(float(v.high) for v in values),
            "low": min(float(v.low) for v in values),
            "close": float(values[-1].close),
            # Never invent volume. Sum only if every contributing source candle
            # has real volume; otherwise keep it unavailable.
            "volume": (
                sum(float(v.volume) for v in values)
                if all(v.volume is not None for v in values)
                else None
            ),
        })

    return _save_candles(db, asset, candles, target_interval)


def _backfill_asset(db: Session, asset: Asset) -> tuple[int, int, int, int]:
    saved_5m = saved_1h = saved_4h = saved_1d = 0

    if not _has_enough(db, asset, 5, MINIMUM_5M_CANDLES):
        points = _fetch_history(asset.symbol, FIVE_MINUTE_DAYS)
        candles = _build_candles(points, 5)
        saved_5m = _save_candles(db, asset, candles, 5) if candles else 0

    if not _has_enough(db, asset, 60, MINIMUM_1H_CANDLES):
        points = _fetch_history(asset.symbol, HOURLY_DAYS, interval="hourly")
        candles = _build_candles(points, 60)
        saved_1h = _save_candles(db, asset, candles, 60) if candles else 0

    # Build higher timeframes from real stored hourly candles.
    if not _has_enough(db, asset, 240, MINIMUM_4H_CANDLES):
        saved_4h = _aggregate_existing(db, asset, 60, 240)

    if not _has_enough(db, asset, 1440, MINIMUM_1D_CANDLES):
        saved_1d = _aggregate_existing(db, asset, 60, 1440)

    return saved_5m, saved_1h, saved_4h, saved_1d


def backfill_coingecko_history_if_needed(db: Session) -> dict:
    assets = db.execute(
        select(Asset).where(
            Asset.asset_type == "crypto",
            Asset.is_active.is_(True),
        ).order_by(Asset.id)
    ).scalars().all()

    totals = {"assets": 0, "success": 0, "failed": 0, "5m": 0, "1h": 0, "4h": 0, "1d": 0}

    for index, asset in enumerate(assets):
        if asset.symbol not in COIN_IDS:
            continue

        totals["assets"] += 1
        try:
            saved_5m, saved_1h, saved_4h, saved_1d = _backfill_asset(db, asset)
            totals["5m"] += saved_5m
            totals["1h"] += saved_1h
            totals["4h"] += saved_4h
            totals["1d"] += saved_1d
            totals["success"] += 1
            print(
                f"[History] {asset.symbol}: "
                f"5m={saved_5m}, 1h={saved_1h}, 4h={saved_4h}, 1d={saved_1d}"
            )
        except Exception as error:
            db.rollback()
            totals["failed"] += 1
            print(f"[History] CoinGecko backfill failed for {asset.symbol}: {error}")

        if index < len(assets) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    print(f"[History] Completed: {totals}")
    return totals
