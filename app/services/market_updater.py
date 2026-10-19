import asyncio


from sqlalchemy import func, text


from app.database import SessionLocal, engine


from app.models.asset import Asset
from app.models.market_price import MarketPrice


from app.services.alert_service import (
    evaluate_all_active_alerts,
    send_pending_alert_notifications,
)


from app.services.market_data_service import (
    get_crypto_prices,
    get_gold_price,
    get_energy_prices,
    get_iran_fx_prices,
    get_afghan_fx_prices,
    get_iran_local_metals_prices,
    get_herat_gold_price,
    save_market_prices,
)


# =========================================================
# Update intervals
# =========================================================

# Crypto prices
# CoinGecko
CRYPTO_UPDATE_INTERVAL = 60


# Global gold
GOLD_UPDATE_INTERVAL = 120


# Oil / Energy
ENERGY_UPDATE_INTERVAL = 60 * 60


# Iran FX
# Servix policy: maximum once every 2 hours
IRAN_FX_UPDATE_INTERVAL =  60 * 60


# Afghanistan FX
# Khorasan + Sarai Shahzada + DAB
AFGHAN_FX_UPDATE_INTERVAL = 10 * 60


# Iran local metals
IRAN_METALS_UPDATE_INTERVAL = 60


# Herat gold
HERAT_GOLD_UPDATE_INTERVAL = 60


# Alerts
ALERTS_UPDATE_INTERVAL = 60


# =========================================================
# Market updater distributed lock
# =========================================================

# PostgreSQL advisory lock ID.
# Only one Gunicorn worker is allowed to run the market updater.
MARKET_UPDATER_LOCK_ID = 847291


def acquire_market_updater_lock():
    """
    Acquire the PostgreSQL advisory lock.

    This function is synchronous on purpose. It is called through
    asyncio.to_thread() so PostgreSQL connection work never blocks
    FastAPI's event loop.
    """
    connection = engine.connect()

    try:
        acquired = connection.execute(
            text(
                "SELECT pg_try_advisory_lock(:lock_id)"
            ),
            {
                "lock_id": MARKET_UPDATER_LOCK_ID
            }
        ).scalar()

        if acquired:
            print(
                "[Market] "
                "Market updater lock acquired."
            )
            return connection

        print(
            "[Market] "
            "Another worker already owns the "
            "market updater lock."
        )

        connection.close()
        return None

    except Exception:
        connection.close()
        raise


def release_market_updater_lock(connection):
    """
    Release the PostgreSQL advisory lock.
    """
    if connection is None:
        return

    try:
        connection.execute(
            text(
                "SELECT pg_advisory_unlock(:lock_id)"
            ),
            {
                "lock_id": MARKET_UPDATER_LOCK_ID
            }
        )

        print(
            "[Market] "
            "Market updater lock released."
        )

    except Exception as error:
        print(
            "[Market] "
            f"Failed to release updater lock: {error}"
        )

    finally:
        connection.close()


# =========================================================
# Iran FX symbols
# =========================================================

IRAN_FX_SYMBOLS = {
    "USD_IRT",
    "EUR_IRT",
    "CNY_IRT",
    "RUB_IRT",
    "GBP_IRT",
    "AED_IRT",
    "TRY_IRT",
    "INR_IRT",
    "CAD_IRT",
    "AUD_IRT",
    "AFN_IRT",
    "IQD_IRT",
}


# =========================================================
# Iran FX freshness check
# =========================================================

def iran_fx_data_is_fresh(db) -> bool:
    """
    Treat the latest successfully saved USD_IRT price as the
    marker for the last successful Servix FX update.

    Servix always requires USD_RLS to build USD_IRT. Therefore,
    a recent USD_IRT database row indicates that the Servix
    request returned usable data and the save operation reached
    the database. Missing or older than 2-hour data is stale.

    This avoids depending on every optional FX symbol being
    present in the response and prevents the updater from
    remaining stale just because Servix omits one optional pair.
    """

    recent_usd_marker = (
        db.query(MarketPrice.id)
        .join(
            Asset,
            Asset.id == MarketPrice.asset_id
        )
        .filter(
            Asset.symbol == "USD_IRT",
            Asset.is_active.is_(True),
            MarketPrice.recorded_at
            >= func.now()
            - text("INTERVAL '2 hours'"),
        )
        .order_by(MarketPrice.recorded_at.desc())
        .first()
    )

    return recent_usd_marker is not None


# =========================================================
# Build Iran local metals prices
# =========================================================

def build_iran_metals_prices(
    data: dict
) -> dict:

    prices = {}

    for item in data.get(
        "data",
        []
    ):

        symbol = item.get(
            "symbol"
        )

        price = item.get(
            "price"
        )

        if not symbol:
            continue

        if price is None:
            continue

        prices[symbol] = {
            "price": price,
            "change_24h": (
                item.get(
                    "change_24h",
                    0
                )
                or 0
            ),
            "volume_24h": None,
            "market_cap": None,
        }

    return prices


# =========================================================
# Build Herat gold prices
# =========================================================

def build_herat_gold_prices(
    data: dict
) -> dict:

    prices = {}

    gold = data.get(
        "gold",
        {}
    )

    coins = data.get(
        "coins",
        {}
    )

    # -----------------------------------------------------
    # 18K
    # -----------------------------------------------------

    gold_18k = gold.get(
        "18K"
    )

    if gold_18k:

        price = gold_18k.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_GOLD_18K"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    # -----------------------------------------------------
    # 21K
    # -----------------------------------------------------

    gold_21k = gold.get(
        "21K"
    )

    if gold_21k:

        price = gold_21k.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_GOLD_21K"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    # -----------------------------------------------------
    # Quarter coin
    # -----------------------------------------------------

    quarter = coins.get(
        "quarter"
    )

    if quarter:

        price = quarter.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_COIN_QUARTER"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    # -----------------------------------------------------
    # Half coin
    # -----------------------------------------------------

    half = coins.get(
        "half"
    )

    if half:

        price = half.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_COIN_HALF"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    # -----------------------------------------------------
    # Full coin
    # -----------------------------------------------------

    full = coins.get(
        "full"
    )

    if full:

        price = full.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_COIN_FULL"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    # -----------------------------------------------------
    # Melted gold
    # -----------------------------------------------------

    melted = data.get(
        "melted_gold"
    )

    if melted:

        price = melted.get(
            "price"
        )

        if price is not None:

            prices[
                "HERAT_MELTED_GOLD"
            ] = {
                "price": price,
                "change_24h": 0,
                "volume_24h": None,
                "market_cap": None,
            }

    return prices


# =========================================================
# Generic database save helper
# =========================================================

def save_prices_to_database(
    prices: dict
) -> int:

    if not prices:
        return 0

    db = SessionLocal()

    try:

        saved = save_market_prices(
            db,
            prices
        )

        return saved

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


# =========================================================
# Crypto update
# =========================================================

def update_crypto_sync():

    crypto_prices = get_crypto_prices()

    received = len(
        crypto_prices
    )

    saved = save_prices_to_database(
        crypto_prices
    )

    print(
        "[Market] "
        f"Crypto updated: "
        f"{saved}/{received}"
    )


# =========================================================
# Global gold update
# =========================================================

def update_gold_sync():

    gold_price = get_gold_price()

    if not gold_price:
        return

    saved = save_prices_to_database(
        {
            "GOLD": gold_price
        }
    )

    print(
        "[Market] "
        f"Global Gold updated: "
        f"{saved}"
    )


# =========================================================
# Iran local metals update
# =========================================================

def update_iran_metals_sync():

    # Force a fresh TGJU request instead of reusing an old persistent cache.
    data = get_iran_local_metals_prices(force_refresh=True)

    prices = build_iran_metals_prices(
        data
    )

    if not prices:

        print(
            "[Market] "
            "Iran metals returned no prices."
        )

        return

    saved = save_prices_to_database(
        prices
    )

    print(
        "[Market] "
        f"Iran metals updated: "
        f"{saved}"
    )


# =========================================================
# Herat gold update
# =========================================================

def update_herat_gold_sync():

    data = get_herat_gold_price()

    prices = build_herat_gold_prices(
        data
    )

    if not prices:

        print(
            "[Market] "
            "Herat gold returned no prices."
        )

        return

    saved = save_prices_to_database(
        prices
    )

    print(
        "[Market] "
        f"Herat gold updated: "
        f"{saved}"
    )


# =========================================================
# Energy / Oil update
# =========================================================

def update_energy_sync():

    prices = get_energy_prices()

    if not prices:

        print(
            "[Market] "
            "Energy source returned no prices."
        )

        return

    saved = save_prices_to_database(
        prices
    )

    print(
        "[Market] "
        f"Energy / Oil updated: "
        f"{saved}"
    )


# =========================================================
# Iran FX update
# =========================================================

def update_iran_fx_sync():

    db = SessionLocal()

    try:

        if iran_fx_data_is_fresh(db):

            print(
                "[Market] "
                "Iran FX skipped: "
                "database data is still fresh."
            )

            return

    finally:

        db.close()

    prices = get_iran_fx_prices()

    if not prices:

        print(
            "[Market] "
            "Iran FX returned no prices."
        )

        return

    saved = save_prices_to_database(
        prices
    )

    print(
        "[Market] "
        f"Iran FX updated: "
        f"{saved}"
    )


# =========================================================
# Afghanistan FX update
# =========================================================

def update_afghan_fx_sync():

    prices = get_afghan_fx_prices()

    if not prices:

        print(
            "[Market] "
            "Afghanistan FX returned no prices."
        )

        return

    saved = save_prices_to_database(
        prices
    )

    print(
        "[Market] "
        f"Afghanistan FX updated: "
        f"{saved}"
    )


# =========================================================
# Alerts
# =========================================================

def evaluate_market_alerts():

    db = SessionLocal()

    try:

        try:

            triggered_alerts = (
                evaluate_all_active_alerts(
                    db
                )
            )

            if triggered_alerts:

                print(
                    "[Alerts] "
                    f"Triggered: "
                    f"{triggered_alerts}"
                )

            sent_notifications = (
                send_pending_alert_notifications(
                    db
                )
            )

            if sent_notifications:

                print(
                    "[NTFY] "
                    f"Notifications sent: "
                    f"{sent_notifications}"
                )

        except Exception as error:

            db.rollback()

            print(
                "[Alerts] "
                f"Alert evaluation failed: "
                f"{error}"
            )

    finally:

        db.close()


# =========================================================
# Generic periodic worker
# =========================================================

async def run_periodic_worker(
    name: str,
    interval: int,
    function,
):
    """
    Run a blocking/synchronous market function in a worker
    thread so that FastAPI's asyncio event loop is never
    blocked by urllib/database operations.

    The function is executed immediately on startup.
    After it finishes, the worker waits for the configured
    interval and runs again.
    """

    print(
        "[Market] "
        f"{name} worker started "
        f"(interval={interval}s)"
    )

    while True:

        started_at = (
            asyncio.get_running_loop().time()
        )

        try:

            await asyncio.to_thread(
                function
            )

            elapsed = (
                asyncio.get_running_loop().time()
                - started_at
            )

            print(
                "[Market] "
                f"{name} update completed successfully "
                f"in {elapsed:.2f}s."
            )

        except asyncio.CancelledError:

            print(
                "[Market] "
                f"{name} worker cancelled."
            )

            raise

        except Exception as error:

            print(
                "[Market] "
                f"{name} update failed: "
                f"{error}"
            )

        elapsed = (
            asyncio.get_running_loop().time()
            - started_at
        )

        # Do not start the next update while the
        # previous update is still running.
        sleep_time = max(
            0,
            interval - elapsed
        )

        await asyncio.sleep(
            sleep_time
        )


# =========================================================
# Main market updater
# =========================================================

async def update_market_prices():
    """
    Main background market updater.

    The updater uses a PostgreSQL advisory lock so only one
    Gunicorn worker runs it.

    Each market source runs independently. If one source fails,
    the other sources continue running.
    """

    print(
        "[Market] "
        "Starting market updater..."
    )

    # Acquire the distributed lock without blocking
    # FastAPI's asyncio event loop.
    try:
        lock_connection = await asyncio.to_thread(
            acquire_market_updater_lock
        )
    except Exception as error:
        print(
            "[Market] "
            f"Could not acquire updater lock: {error}"
        )
        return

    if lock_connection is None:
        print(
            "[Market] "
            "Updater is disabled in this Gunicorn worker "
            "because another worker owns the lock."
        )
        return

    print(
        "[Market] "
        "Market updater started successfully."
    )

    print(
        "[Market] "
        "Architecture: "
        "External sources -> Database -> API -> Frontend"
    )

    print(
        "[Market] "
        "Database-backed price updates are enabled."
    )

    print(
        "[Market] "
        "Crypto=60s | Gold=120s | Metals=60s | "
        "Herat Gold=60s | Energy=3600s | "
        "Iran FX=7200s | Afghanistan FX=600s | "
        "Alerts=60s"
    )

    workers = []

    try:
        workers = [
            asyncio.create_task(
                run_periodic_worker(
                    "Crypto",
                    CRYPTO_UPDATE_INTERVAL,
                    update_crypto_sync,
                ),
                name="market-crypto"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Global Gold",
                    GOLD_UPDATE_INTERVAL,
                    update_gold_sync,
                ),
                name="market-global-gold"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Iran Metals",
                    IRAN_METALS_UPDATE_INTERVAL,
                    update_iran_metals_sync,
                ),
                name="market-iran-metals"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Herat Gold",
                    HERAT_GOLD_UPDATE_INTERVAL,
                    update_herat_gold_sync,
                ),
                name="market-herat-gold"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Energy / Oil",
                    ENERGY_UPDATE_INTERVAL,
                    update_energy_sync,
                ),
                name="market-energy"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Iran FX",
                    IRAN_FX_UPDATE_INTERVAL,
                    update_iran_fx_sync,
                ),
                name="market-iran-fx"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Afghanistan FX",
                    AFGHAN_FX_UPDATE_INTERVAL,
                    update_afghan_fx_sync,
                ),
                name="market-afghanistan-fx"
            ),

            asyncio.create_task(
                run_periodic_worker(
                    "Alerts",
                    ALERTS_UPDATE_INTERVAL,
                    evaluate_market_alerts,
                ),
                name="market-alerts"
            ),
        ]

        print(
            "[Market] "
            f"{len(workers)} periodic workers started."
        )

        await asyncio.gather(*workers)

    except asyncio.CancelledError:
        print(
            "[Market] "
            "Market updater stopping..."
        )

        for worker in workers:
            worker.cancel()

        await asyncio.gather(
            *workers,
            return_exceptions=True
        )

        raise

    except Exception as error:
        print(
            "[Market] "
            f"Market updater stopped unexpectedly: {error}"
        )

        for worker in workers:
            worker.cancel()

        await asyncio.gather(
            *workers,
            return_exceptions=True
        )

        raise

    finally:
        await asyncio.to_thread(
            release_market_updater_lock,
            lock_connection
        )

        print(
            "[Market] "
            "Market updater shutdown complete."
        )

