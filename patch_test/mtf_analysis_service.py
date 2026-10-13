from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services.technical_analysis_service import analyze_asset

TIMEFRAMES = ("5m", "15m", "30m", "1h", "4h", "1d")

# MTF weights: shorter timeframes are useful for entry context, while
# higher timeframes carry more weight for the overall regime.
TIMEFRAME_WEIGHTS = {
    "5m": 1,
    "15m": 1,
    "30m": 1,
    "1h": 2,
    "4h": 3,
    "1d": 4,
}


def _direction_points(analysis: dict) -> tuple[int, int]:
    if not analysis.get("ready"):
        return 0, 0

    signal = analysis.get("signal") or {}
    bullish = int(signal.get("bullish_points") or 0)
    bearish = int(signal.get("bearish_points") or 0)
    return bullish, bearish


def _regime(analyses: dict[str, dict]) -> str:
    ready = [value for value in analyses.values() if value.get("ready")]
    if not ready:
        return "Insufficient Data"

    up = down = 0
    for analysis in ready:
        state = ((analysis.get("trend") or {}).get("state") or "").lower()
        if "uptrend" in state:
            up += 1
        elif "downtrend" in state:
            down += 1

    if up > down:
        return "Uptrend"
    if down > up:
        return "Downtrend"
    return "Mixed"


def _weighted_bias(analyses: dict[str, dict]) -> dict:
    weighted_bullish = 0
    weighted_bearish = 0
    ready_count = 0

    for timeframe, analysis in analyses.items():
        if not analysis.get("ready"):
            continue
        ready_count += 1
        bullish, bearish = _direction_points(analysis)
        weight = TIMEFRAME_WEIGHTS[timeframe]
        weighted_bullish += bullish * weight
        weighted_bearish += bearish * weight

    total = weighted_bullish + weighted_bearish

    if ready_count == 0:
        bias = "Insufficient Data"
    elif total == 0:
        bias = "Neutral"
    elif weighted_bullish - weighted_bearish >= 12:
        bias = "Bullish"
    elif weighted_bearish - weighted_bullish >= 12:
        bias = "Bearish"
    elif weighted_bullish > weighted_bearish:
        bias = "Slightly Bullish"
    elif weighted_bearish > weighted_bullish:
        bias = "Slightly Bearish"
    else:
        bias = "Balanced"

    return {
        "bias": bias,
        "weighted_bullish_points": weighted_bullish,
        "weighted_bearish_points": weighted_bearish,
        "ready_timeframes": ready_count,
        "total_timeframes": len(TIMEFRAMES),
    }


def analyze_multi_timeframe(
    db: Session,
    asset: Asset,
    period: str = "30d",
) -> dict:
    analyses: dict[str, dict] = {}

    for timeframe in TIMEFRAMES:
        try:
            analyses[timeframe] = analyze_asset(
                db,
                asset,
                timeframe=timeframe,
                period=period,
            )
        except Exception as error:
            analyses[timeframe] = {
                "timeframe": timeframe,
                "ready": False,
                "reason": f"Analysis error: {error}",
            }

    weighted = _weighted_bias(analyses)

    alignment = []
    for timeframe in TIMEFRAMES:
        analysis = analyses[timeframe]
        signal = analysis.get("signal") or {}
        alignment.append({
            "timeframe": timeframe,
            "ready": bool(analysis.get("ready")),
            "bias": signal.get("bias") if analysis.get("ready") else "Insufficient Data",
            "bullish_points": signal.get("bullish_points") if analysis.get("ready") else 0,
            "bearish_points": signal.get("bearish_points") if analysis.get("ready") else 0,
        })

    return {
        "symbol": asset.symbol,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "quote_currency": asset.quote_currency,
        "period": period,
        "timeframes": analyses,
        "summary": {
            **weighted,
            "regime": _regime(analyses),
            "alignment": alignment,
            "note": (
                "MTF is a weighted interpretation of the available technical "
                "signals across timeframes; it is not a guaranteed forecast."
            ),
        },
    }
