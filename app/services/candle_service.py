from __future__ import annotations



from datetime import datetime



from sqlalchemy import func, select

from sqlalchemy.dialects.postgresql import insert

from sqlalchemy.orm import Session



from app.models.asset import Asset

from app.models.market_candle import MarketCandle

from app.models.market_price import MarketPrice





SUPPORTED_INTERVALS = {

    1,

    5,

    15,

    30,

    60,

    240,

    1440,

}



# تاریخچه‌ای که از CoinGecko وارد کردیم روی 5 دقیقه است.

BASE_HISTORY_INTERVAL = 5





# ============================================================

# Time helpers

# ============================================================



def floor_timestamp(

    timestamp: datetime,

    interval_minutes: int,

) -> datetime:



    if interval_minutes <= 0:

        raise ValueError(

            "interval_minutes must be positive"

        )



    timestamp = timestamp.replace(

        second=0,

        microsecond=0,

    )



    total_minutes = (

        timestamp.hour * 60

        + timestamp.minute

    )



    floored_minutes = (

        total_minutes // interval_minutes

    ) * interval_minutes



    return timestamp.replace(

        hour=floored_minutes // 60,

        minute=floored_minutes % 60,

    )





# ============================================================

# Core upsert

# ============================================================



def _upsert_candle(

    db: Session,

    *,

    asset_id: int,

    interval_minutes: int,

    recorded_at: datetime,

    open_price: float,

    high_price: float,

    low_price: float,

    close_price: float,

    volume: float | None,

) -> None:



    table = MarketCandle.__table__



    statement = insert(table).values(

        asset_id=asset_id,

        interval_minutes=interval_minutes,

        open=open_price,

        high=high_price,

        low=low_price,

        close=close_price,

        volume=volume,

        recorded_at=recorded_at,

    )



    excluded = statement.excluded



    statement = statement.on_conflict_do_update(

        constraint=(

            "uq_market_candles_asset_interval_time"

        ),

        set_={

            # Open باید مقدار اولیه همان کندل بماند.

            "open": table.c.open,



            # High/Low در طول تشکیل کندل به‌روزرسانی می‌شوند.

            "high": func.greatest(

                table.c.high,

                excluded.high,

            ),



            "low": func.least(

                table.c.low,

                excluded.low,

            ),



            # آخرین قیمت = Close

            "close": excluded.close,



            # اگر volume واقعی داریم، ذخیره کن.

            # اگر None است، volume قبلی را پاک نکن.

            "volume": (

                excluded.volume

                if volume is not None

                else table.c.volume

            ),

        },

    )



    db.execute(statement)





# ============================================================

# 1 Minute snapshot candle

# ============================================================



def upsert_one_minute_candle(

    db: Session,

    asset: Asset,

    price: float,

    recorded_at: datetime,

    volume: float | None = None,

) -> None:

    """

    ثبت قیمت Snapshot به عنوان کندل 1 دقیقه‌ای.



    همچنین همان Snapshot را در کندل 5 دقیقه‌ای وارد می‌کند

    تا بعد از پایان تاریخچه CoinGecko، داده زنده نیز به همان

    pipeline پنج دقیقه‌ای ادامه پیدا کند.



    توجه:

    volume نباید rolling 24h volume باشد.

    """



    price = float(price)



    # --------------------------------------------------------

    # 1m

    # --------------------------------------------------------



    one_minute_bucket = floor_timestamp(

        recorded_at,

        1,

    )



    _upsert_candle(

        db,

        asset_id=asset.id,

        interval_minutes=1,

        recorded_at=one_minute_bucket,

        open_price=price,

        high_price=price,

        low_price=price,

        close_price=price,

        volume=volume,

    )



    # --------------------------------------------------------

    # 5m

    # --------------------------------------------------------



    five_minute_bucket = floor_timestamp(

        recorded_at,

        BASE_HISTORY_INTERVAL,

    )



    _upsert_candle(

        db,

        asset_id=asset.id,

        interval_minutes=BASE_HISTORY_INTERVAL,

        recorded_at=five_minute_bucket,

        open_price=price,

        high_price=price,

        low_price=price,

        close_price=price,

        volume=volume,

    )





# ============================================================

# External OHLCV candle

# ============================================================



def upsert_kraken_ohlcv_candle(
    db: Session,
    asset: Asset,
    *,
    recorded_at: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float | None,
    interval_minutes: int,
) -> None:
    if interval_minutes not in {1, 5}:
        raise ValueError(f"Unsupported Kraken interval: {interval_minutes}")
    _upsert_candle(
        db,
        asset_id=asset.id,
        interval_minutes=interval_minutes,
        recorded_at=floor_timestamp(recorded_at, interval_minutes),
        open_price=float(open_price),
        high_price=float(high_price),
        low_price=float(low_price),
        close_price=float(close_price),
        volume=float(volume) if volume is not None else None,
    )


def upsert_external_ohlcv_candle(

    db: Session,

    asset: Asset,

    *,

    recorded_at: datetime,

    open_price: float,

    high_price: float,

    low_price: float,

    close_price: float,

    volume: float | None,

    interval_minutes: int = 1,

) -> None:

    """

    ثبت کندل OHLCV دریافت‌شده از Provider.



    این تابع برای داده‌هایی است که واقعاً OHLC دارند.



    در معماری فعلی پروژه، تاریخچه CoinGecko از طریق

    historical_backfill_service مستقیماً به کندل‌های 5m

    تبدیل می‌شود.

    """



    if interval_minutes not in SUPPORTED_INTERVALS:

        raise ValueError(

            f"Unsupported interval: {interval_minutes}. "

            f"Supported: {sorted(SUPPORTED_INTERVALS)}"

        )



    bucket = floor_timestamp(

        recorded_at,

        interval_minutes,

    )



    _upsert_candle(

        db,

        asset_id=asset.id,

        interval_minutes=interval_minutes,

        recorded_at=bucket,

        open_price=float(open_price),

        high_price=float(high_price),

        low_price=float(low_price),

        close_price=float(close_price),

        volume=(

            float(volume)

            if volume is not None

            else None

        ),

    )





# ============================================================

# Compatibility: backfill 1m from MarketPrice

# ============================================================



def backfill_one_minute_candles(

    db: Session,

    asset: Asset,

    limit: int = 200,

) -> int:

    """

    Backfill snapshot-based 1m candles from MarketPrice.



    برای سازگاری با بخش‌های قبلی پروژه نگه داشته شده است.

    """



    if limit <= 0:

        return 0



    query = (

        select(MarketPrice)

        .where(

            MarketPrice.asset_id == asset.id

        )

        .order_by(

            MarketPrice.recorded_at.desc()

        )

        .limit(limit)

    )



    prices = list(

        reversed(

            db.execute(query)

            .scalars()

            .all()

        )

    )



    for item in prices:



        upsert_one_minute_candle(

            db=db,

            asset=asset,

            price=float(item.price),

            recorded_at=item.recorded_at,

            volume=None,

        )



    if prices:

        db.flush()



    return len(prices)





# ============================================================

# Determine base interval

# ============================================================



def _get_base_interval(
    interval_minutes: int,
) -> int:
    if interval_minutes == 1:
        return 1
    if interval_minutes in {5, 15, 30}:
        return 5
    if interval_minutes in {60, 240}:
        return 60
    if interval_minutes == 1440:
        return 1440
    raise ValueError(
        f"Unsupported interval: {interval_minutes}"
    )


# Get candles

# ============================================================



def get_candles(

    db: Session,

    asset: Asset,

    interval_minutes: int,

    start_time: datetime | None = None,

    end_time: datetime | None = None,

) -> list[dict]:

    """

    Return candles at requested timeframe.



    Data pipeline:



        1m

         └──> 1m analysis



        5m

         ├──> 5m

         ├──> 15m

         ├──> 30m

         ├──> 1h

         ├──> 4h

         └──> 1d



    تاریخچه CoinGecko در 5m ذخیره شده است.

    """



    if interval_minutes not in SUPPORTED_INTERVALS:

        raise ValueError(

            f"Unsupported interval: {interval_minutes}. "

            f"Supported: {sorted(SUPPORTED_INTERVALS)}"

        )



    base_interval = _get_base_interval(

        interval_minutes

    )



    query = (

        select(MarketCandle)

        .where(

            MarketCandle.asset_id == asset.id,

            MarketCandle.interval_minutes

            == base_interval,

        )

        .order_by(

            MarketCandle.recorded_at.asc()

        )

    )



    if start_time is not None:

        query = query.where(

            MarketCandle.recorded_at >= start_time

        )



    if end_time is not None:

        query = query.where(

            MarketCandle.recorded_at <= end_time

        )



    rows = (

        db.execute(query)

        .scalars()

        .all()

    )



    if not rows:

        return []



    # --------------------------------------------------------

    # Native timeframe

    # --------------------------------------------------------



    if interval_minutes == base_interval:



        return [

            format_candle(row)

            for row in rows

        ]



    # --------------------------------------------------------

    # Aggregate base candles

    # --------------------------------------------------------



    grouped: dict[

        datetime,

        list[MarketCandle],

    ] = {}



    for row in rows:



        bucket = floor_timestamp(

            row.recorded_at,

            interval_minutes,

        )



        grouped.setdefault(

            bucket,

            [],

        ).append(row)



    result = []



    for bucket, group in sorted(

        grouped.items()

    ):



        ordered = sorted(

            group,

            key=lambda item: item.recorded_at,

        )



        if not ordered:

            continue



        volumes = [

            float(item.volume)

            for item in ordered

            if item.volume is not None

        ]



        result.append(

            {

                "timestamp": bucket.isoformat(),



                # Open = اولین کندل بازه

                "open": float(

                    ordered[0].open

                ),



                # High = بالاترین High

                "high": max(

                    float(item.high)

                    for item in ordered

                ),



                # Low = پایین‌ترین Low

                "low": min(

                    float(item.low)

                    for item in ordered

                ),



                # Close = آخرین کندل بازه

                "close": float(

                    ordered[-1].close

                ),



                # فقط volume واقعی را جمع می‌کنیم.

                # اگر volume نداریم، None.

                "volume": (

                    sum(volumes)

                    if volumes

                    else None

                ),

            }

        )



    return result





# ============================================================

# Format candle

# ============================================================



def format_candle(

    candle: MarketCandle,

) -> dict:



    return {

        "timestamp": (

            candle.recorded_at.isoformat()

        ),



        "open": float(

            candle.open

        ),



        "high": float(

            candle.high

        ),



        "low": float(

            candle.low

        ),



        "close": float(

            candle.close

        ),



        "volume": (

            float(candle.volume)

            if candle.volume is not None

            else None

        ),

    }