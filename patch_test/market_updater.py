import asyncio

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models.asset import Asset
from app.models.market_price import MarketPrice

from app.services.market_data_service import (
    get_crypto_prices,
    get_gold_price,
    get_energy_prices,
    get_iran_fx_prices,
    get_afghan_fx_prices,
    save_market_prices,
)
from app.services.historical_backfill_service import backfill_coingecko_history_if_needed

CRYPTO_UPDATE_INTERVAL = 60
GOLD_UPDATE_INTERVAL = 120
ENERGY_UPDATE_INTERVAL = 60 * 60
IRAN_FX_UPDATE_INTERVAL = 2 * 60 * 60
AFGHAN_FX_UPDATE_INTERVAL = 10 * 60

IRAN_FX_SYMBOLS = {
    "USD_IRT", "EUR_IRT", "CNY_IRT", "RUB_IRT", "GBP_IRT", "AED_IRT",
    "TRY_IRT", "INR_IRT", "CAD_IRT", "AUD_IRT", "AFN_IRT", "IQD_IRT",
}


def iran_fx_data_is_fresh(db) -> bool:
    recent_count = (
        db.query(func.count(func.distinct(MarketPrice.asset_id)))
        .join(Asset, Asset.id == MarketPrice.asset_id)
        .filter(
            Asset.symbol.in_(IRAN_FX_SYMBOLS),
            Asset.is_active.is_(True),
            MarketPrice.recorded_at >= func.now() - text("INTERVAL '2 hours'"),
        )
        .scalar()
    )
    return (recent_count or 0) >= len(IRAN_FX_SYMBOLS)


async def update_market_prices():
    last_gold_update = 0
    last_energy_update = 0
    last_iran_fx_update = 0
    last_afghan_fx_update = 0

    print("[Market] Market updater started")

    # Historical crypto backfill runs once at startup.
    db = SessionLocal()
    try:
        try:
            saved = await asyncio.to_thread(backfill_coingecko_history_if_needed, db)
            print(f"[History] Startup backfill completed: {saved}")
        except Exception as error:
            db.rollback()
            print(f"[History] Startup backfill failed: {error}")
    finally:
        db.close()

    print(
        "[Market] Servix Iran FX policy: "
        "maximum 1 request every 2 hours, with database freshness protection."
    )

    while True:
        current_time = asyncio.get_running_loop().time()

        db = SessionLocal()
        try:
            try:
                crypto_prices = get_crypto_prices()
                crypto_saved = save_market_prices(db, crypto_prices)
                print(f"[Market] Crypto prices updated: {crypto_saved}")
            except Exception as error:
                db.rollback()
                print(f"[Market] Crypto price update failed: {error}")
        finally:
            db.close()

        if current_time - last_gold_update >= GOLD_UPDATE_INTERVAL:
            db = SessionLocal()
            try:
                try:
                    gold_price = get_gold_price()
                    gold_saved = save_market_prices(db, {"GOLD": gold_price})
                    last_gold_update = current_time
                    print(f"[Market] Gold updated: {gold_saved}")
                except Exception as error:
                    db.rollback()
                    print(f"[Market] Gold update failed: {error}")
            finally:
                db.close()

        if current_time - last_energy_update >= ENERGY_UPDATE_INTERVAL:
            db = SessionLocal()
            try:
                try:
                    energy_prices = get_energy_prices()
                    energy_saved = save_market_prices(db, energy_prices)
                    last_energy_update = current_time
                    print(f"[Market] Energy updated: {energy_saved}")
                except Exception as error:
                    db.rollback()
                    print(f"[Market] Energy update failed: {error}")
            finally:
                db.close()

        if current_time - last_iran_fx_update >= IRAN_FX_UPDATE_INTERVAL:
            db = SessionLocal()
            try:
                try:
                    if iran_fx_data_is_fresh(db):
                        last_iran_fx_update = current_time
                        print("[Market] Iran FX skipped: database data is still fresh.")
                    else:
                        iran_fx_prices = get_iran_fx_prices()
                        iran_fx_saved = save_market_prices(db, iran_fx_prices)
                        last_iran_fx_update = current_time
                        print(f"[Market] Iran FX updated: {iran_fx_saved}")
                except Exception as error:
                    db.rollback()
                    last_iran_fx_update = current_time
                    print(f"[Market] Iran FX update failed: {error}")
            finally:
                db.close()

        if current_time - last_afghan_fx_update >= AFGHAN_FX_UPDATE_INTERVAL:
            db = SessionLocal()
            try:
                try:
                    afghan_fx_prices = get_afghan_fx_prices()
                    afghan_fx_saved = save_market_prices(db, afghan_fx_prices)
                    last_afghan_fx_update = current_time
                    print(f"[Market] Afghanistan FX updated: {afghan_fx_saved}")
                except Exception as error:
                    db.rollback()
                    print(f"[Market] Afghanistan FX update failed: {error}")
            finally:
                db.close()

        await asyncio.sleep(CRYPTO_UPDATE_INTERVAL)
