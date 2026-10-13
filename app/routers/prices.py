from datetime import datetime, timedelta







from fastapi import (

    APIRouter,

    BackgroundTasks,

    Depends,



    HTTPException



)







from sqlalchemy import (



    select,



    desc



)







from sqlalchemy.orm import Session







from app.database import get_db







from app.models.asset import Asset



from app.models.market_price import MarketPrice



from app.services.candle_service import get_candles







from app.services.market_data_service import (



    get_crypto_prices,



    get_gold_price,



    get_energy_prices,



    get_all_market_prices,



    save_market_prices,



    get_iran_local_metals_prices,



    get_cached_iran_local_metals_prices,

    get_herat_gold_price,

    get_cached_herat_gold_price,

    herat_gold_cache_is_fresh,

    ensure_coingecko_history,



)











router = APIRouter(



    prefix="/api/prices",



    tags=["Prices"]



)











# =========================================================



# Helpers



# =========================================================







def get_asset_by_symbol(



    db: Session,



    symbol: str



):







    symbol = symbol.upper()







    result = db.execute(



        select(Asset)



        .where(



            Asset.symbol == symbol,



            Asset.is_active == True



        )



    )







    return result.scalar_one_or_none()











def get_latest_market_price(



    db: Session,



    asset: Asset



):







    result = db.execute(



        select(MarketPrice)



        .where(



            MarketPrice.asset_id == asset.id



        )



        .order_by(



            desc(MarketPrice.recorded_at)



        )



        .limit(1)



    )







    return result.scalars().first()











def format_market_price(
    asset: Asset,
    market_price: MarketPrice
):
    source = None

    if asset.asset_type == "forex":
        if asset.quote_currency == "AFN":
            # Afghanistan FX source is stored in Asset.network.
            source_map = {
                "Khorasan Market": "Khorasan Market",
                "Sarai Shahzada": "Sarai Shahzada",
                "Da Afghanistan Bank": "Da Afghanistan Bank",
            }
            source = source_map.get(asset.network, asset.network)
        elif asset.quote_currency == "IRT":
            source = "Servix"

    return {




        "id": asset.id,



        "symbol": asset.symbol,



        "name": asset.name,



        "network": asset.network,



        "asset_type": asset.asset_type,



        "quote_currency": asset.quote_currency,



        "source": source,



        "price": float(



            market_price.price



        ),



        "change_24h": float(



            market_price.change_24h



        ),



        "volume_24h": (



            float(



                market_price.volume_24h



            )



            if market_price.volume_24h is not None



            else None



        ),



        "market_cap": (



            float(



                market_price.market_cap



            )



            if market_price.market_cap is not None



            else None



        ),



        "recorded_at":



            market_price.recorded_at



    }











# =========================================================



# Crypto prices from API



# =========================================================







@router.get("/crypto")
@router.get("/crypto/latest")
def crypto_prices(
    db: Session = Depends(get_db),
):
    """
    Return the latest crypto price snapshots saved in PostgreSQL.

    CoinGecko is called by the background market updater, not by this
    endpoint. Reading MarketPrice here ensures that recorded_at reflects
    the actual database snapshot time.
    """
    try:
        assets = db.execute(
            select(Asset)
            .where(
                Asset.asset_type == "crypto",
                Asset.is_active == True,
            )
            .order_by(Asset.symbol)
        ).scalars().all()

        data = []

        for asset in assets:
            market_price = get_latest_market_price(db, asset)

            # Skip assets that have not received their first price yet.
            if market_price is None:
                continue

            data.append({
                "id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "network": asset.network,
                "asset_type": "crypto",
                "quote_currency": asset.quote_currency or "USDT",
                "source": "CoinGecko",
                "price": float(market_price.price),
                "change_24h": float(market_price.change_24h or 0),
                "volume_24h": (
                    float(market_price.volume_24h)
                    if market_price.volume_24h is not None
                    else None
                ),
                "market_cap": (
                    float(market_price.market_cap)
                    if market_price.market_cap is not None
                    else None
                ),
                "recorded_at": market_price.recorded_at,
            })

        return {
            "category": "crypto",
            "source": "CoinGecko",
            "quote_currency": "USDT",
            "count": len(data),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error while reading crypto prices: {str(e)}",
        )


# =========================================================

# Gold price



# =========================================================







@router.get("/gold")
@router.get("/gold/latest")
def gold_price():







    try:







        price = get_gold_price()







        return {



            "category": "precious_metals",



            "symbol": "GOLD",



            "name": "Gold",



            "quote_currency": "USD",



            "data": price



        }







    except Exception as e:







        raise HTTPException(



            status_code=502,



            detail=(



                f"Gold API error: {str(e)}"



            )



        )











# =========================================================



# Oil / Energy prices



# =========================================================







@router.get("/oil")



def oil_prices(



    db: Session = Depends(get_db)



):







    result = []







    oil_symbols = [



        "BRENT",



        "WTI",



        "URALS"



    ]







    for symbol in oil_symbols:







        asset = get_asset_by_symbol(



            db,



            symbol



        )







        if not asset:



            continue







        market_price = get_latest_market_price(



            db,



            asset



        )







        if not market_price:



            continue







        result.append(



            format_market_price(



                asset,



                market_price



            )



        )







    return {



        "category": "oil",



        "count": len(result),



        "data": result



    }











# =========================================================



# Iranian FX prices



# =========================================================







@router.get("/fx/iran")



def iran_fx_prices(



    db: Session = Depends(get_db)



):



    """



    Latest Iranian FX prices stored in the database.







    Values are displayed in Iranian Toman.



    The updater obtains them from Servix.



    """







    assets_result = db.execute(



        select(Asset)



        .where(



            Asset.asset_type == "forex",



            Asset.quote_currency == "IRT",



            Asset.is_active == True



        )



        .order_by(



            Asset.symbol



        )



    )







    assets = assets_result.scalars().all()







    result = []







    for asset in assets:







        market_price = get_latest_market_price(



            db,



            asset



        )







        if not market_price:



            continue







        result.append(



            format_market_price(



                asset,



                market_price



            )



        )







    return {



        "category": "iran_fx",



        "unit": "IRT",



        "unit_name": "Iranian Toman",



        "count": len(result),



        "data": result



    }











# =========================================================



# Iran local gold + silver prices from TGJU



# =========================================================







@router.get("/gold/iran")



def iran_local_metals_prices(



    db: Session = Depends(get_db)



):



    """



    Latest Iranian local gold, silver and coin prices.







    The endpoint never waits for TGJU. It returns the last



    successful background cache immediately. On first startup,



    it falls back to the latest database snapshots while the



    updater fetches fresh TGJU data in the background.



    """







    try:



        # Read the database first. In-memory caches are per worker and may be stale.
        # The updater persists each successful TGJU refresh to the database.


        # First-start fallback: return the latest database values



        # immediately instead of waiting for TGJU. The updater will



        # populate the full cached response shortly afterwards.



        asset_result = db.execute(



            select(Asset)



            .where(



                Asset.is_active == True,



                (



                    Asset.symbol.like("GOLD%")



                    | Asset.symbol.like("SILVER%")



                    | Asset.symbol.like("COIN%")



                )



            )



            .order_by(Asset.symbol)



        )







        assets = asset_result.scalars().all()



        data = []







        for asset in assets:



            market_price = get_latest_market_price(



                db,



                asset



            )







            if not market_price:



                continue







            data.append({



                "symbol": asset.symbol,



                "name": asset.name,



                "price": float(market_price.price),



                "change_24h": float(market_price.change_24h),



                "currency": "IRT",



                "recorded_at": market_price.recorded_at,



            })







        if data:



            return {



                "category": "iran_precious_metals",



                "currency": "IRT",



                "unit_name": "Iranian Toman",



                "source": "TGJU",



                "source_url": "https://www.tgju.org/local-markets",



                "updated_at": data[0].get("recorded_at"),



                "count": len(data),



                "data": data,



            }







        # If the database has no snapshots yet, try the persistent cache.
        # Do not let an old worker-local cache override database values.
        cached = get_cached_iran_local_metals_prices()
        if cached:
            return cached

        # Bootstrap only: there are no database snapshots or cached values.
        return get_iran_local_metals_prices(force_refresh=True)







    except Exception as e:



        raise HTTPException(



            status_code=502,



            detail=(



                f"Iran local metals source error: {str(e)}"



            )



        )











# =========================================================



# Afghanistan Herat local gold prices



# =========================================================







@router.get("/gold/afghanistan/herat")

def herat_gold_price(

    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),

):

    """Return cached Herat data immediately and refresh it in background."""

    try:

        cached = get_cached_herat_gold_price()

        if cached:

            if not herat_gold_cache_is_fresh():

                background_tasks.add_task(get_herat_gold_price)

            return {

                "category": "afghanistan_gold",

                "city": "Herat",

                "data": cached,

            }



        assets = db.execute(

            select(Asset)

            .where(

                Asset.symbol.like("HERAT_%"),

                Asset.is_active == True,

            )

            .order_by(Asset.symbol)

        ).scalars().all()



        latest_by_symbol = {}

        latest_recorded_at = None

        for asset in assets:

            market_price = get_latest_market_price(db, asset)

            if market_price is None:

                continue

            latest_by_symbol[asset.symbol] = float(market_price.price)

            if (

                latest_recorded_at is None

                or market_price.recorded_at > latest_recorded_at

            ):

                latest_recorded_at = market_price.recorded_at



        if latest_by_symbol:

            gold = {}

            coins = {}

            symbol_map = {

                "HERAT_GOLD_18K": (gold, "18K", "AFN/gram"),

                "HERAT_GOLD_21K": (gold, "21K", "AFN/gram"),

                "HERAT_COIN_QUARTER": (coins, "quarter", "AFN/coin"),

                "HERAT_COIN_HALF": (coins, "half", "AFN/coin"),

                "HERAT_COIN_FULL": (coins, "full", "AFN/coin"),

                "HERAT_GOLD_MELTED": (gold, "melted", "AFN/gram"),

            }

            for symbol, price in latest_by_symbol.items():

                target = symbol_map.get(symbol)

                if not target:

                    continue

                group, name, unit = target

                group[name] = {

                    "price": price,

                    "buy": price,

                    "sell": price,

                    "unit": unit,

                }



            primary = gold.get("18K") or gold.get("21K")

            data = {

                "city": "Herat",

                "currency": "AFN",

                "source": "نرخ طلا و اسعار هرات / اتحادیه زرگران ولایت هرات",

                "source_url": "https://tg.me/herat_gold",

                "updated_at": latest_recorded_at,

                "available_purities": [k for k in ("18K", "21K") if k in gold],

                "gold": {

                    k: v for k, v in gold.items() if k in {"18K", "21K"}

                },

                "coins": coins,

                "fallback_from_database": True,

            }

            if "melted" in gold:

                data["melted_gold"] = gold["melted"]

            if primary:

                data["buy"] = primary["buy"]

                data["sell"] = primary["sell"]

                data["price"] = primary["price"]

                data["unit"] = primary["unit"]

                data["purity"] = "18K" if "18K" in gold else "21K"



            background_tasks.add_task(get_herat_gold_price)

            return {

                "category": "afghanistan_gold",

                "city": "Herat",

                "data": data,

            }



        # Only a true cold-start request waits for the source.

        return {

            "category": "afghanistan_gold",

            "city": "Herat",

            "data": get_herat_gold_price(),

        }

    except Exception as error:

        raise HTTPException(

            status_code=502,

            detail=f"Herat gold source error: {error}",

        )





# =========================================================



# Afghan FX prices



# =========================================================







@router.get("/fx/afghanistan")
def afghanistan_fx_prices(
    source: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Return the latest Afghanistan FX prices stored in the database.

    Supported sources:
      - khorasan -> Khorasan Market
      - sarai_shahzada -> Sarai Shahzada
      - dab -> Da Afghanistan Bank

    Without a source, all Afghanistan FX assets are returned for
    backward compatibility.
    """

    query = (
        select(Asset)
        .where(
            Asset.asset_type == "forex",
            Asset.quote_currency == "AFN",
            Asset.is_active == True,
        )
    )

    source_map = {
        "khorasan": "Khorasan Market",
        "khorasan_market": "Khorasan Market",
        "sarai": "Sarai Shahzada",
        "sarai_shahzada": "Sarai Shahzada",
        "dab": "Da Afghanistan Bank",
        "da_afghanistan_bank": "Da Afghanistan Bank",
    }

    if source:
        source_key = source.strip().lower()
        network = source_map.get(source_key)

        if not network:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid Afghanistan FX source. Allowed values: "
                    "khorasan, sarai_shahzada, dab"
                ),
            )

        # Keep INR_AFN visible in the main Khorasan view.
        # INR_AFN is sourced from Da Afghanistan Bank, while the
        # other displayed Khorasan pairs come from Khorasan Market.
        if source_key in {"khorasan", "khorasan_market"}:
            query = query.where(
                Asset.network.in_(
                    [
                        "Khorasan Market",
                        "Da Afghanistan Bank",
                    ]
                )
            )
        else:
            query = query.where(Asset.network == network)

    assets = db.execute(
        query.order_by(Asset.symbol)
    ).scalars().all()

    result = []

    for asset in assets:
        market_price = get_latest_market_price(db, asset)

        if market_price is None:
            continue

        result.append(
            format_market_price(
                asset,
                market_price,
            )
        )

    return {
        "category": "afghanistan_fx",
        "unit": "AFN",
        "unit_name": "Afghan Afghani",
        "source": (
            source_map.get(source.strip().lower())
            if source
            else "All Afghanistan FX Sources"
        ),
        "count": len(result),
        "data": result,
    }


# =========================================================



# All FX prices



# =========================================================







@router.get("/fx/all")



def all_fx_prices(



    db: Session = Depends(get_db)



):



    """



    Latest Iranian and Afghan FX prices stored in the database.



    """







    assets_result = db.execute(



        select(Asset)



        .where(



            Asset.asset_type == "forex",



            Asset.is_active == True



        )



        .order_by(



            Asset.quote_currency,



            Asset.symbol



        )



    )







    assets = assets_result.scalars().all()







    iran_result = []



    afghanistan_result = []







    for asset in assets:







        market_price = get_latest_market_price(



            db,



            asset



        )







        if not market_price:



            continue







        formatted = format_market_price(



            asset,



            market_price



        )







        if asset.quote_currency == "IRT":



            iran_result.append(formatted)







        elif asset.quote_currency == "AFN":



            afghanistan_result.append(formatted)







    return {



        "category": "fx",



        "iran": {



            "unit": "IRT",



            "unit_name": "Iranian Toman",



            "count": len(iran_result),



            "data": iran_result



        },



        "afghanistan": {



            "unit": "AFN",



            "unit_name": "Afghan Afghani",



            "count": len(afghanistan_result),



            "data": afghanistan_result



        },



        "count": (



            len(iran_result)



            + len(afghanistan_result)



        )



    }











# =========================================================



# Single FX price



# =========================================================







@router.get("/fx/{region}/{symbol}")



def fx_details(



    region: str,



    symbol: str,



    db: Session = Depends(get_db)



):



    """



    Get one latest FX price.







    Examples:



        /api/prices/fx/iran/USD_IRT



        /api/prices/fx/afghanistan/USD_AFN



    """







    region = region.lower()



    symbol = symbol.upper()







    allowed_regions = {



        "iran": "IRT",



        "afghanistan": "AFN"



    }







    quote_currency = allowed_regions.get(



        region



    )







    if not quote_currency:







        raise HTTPException(



            status_code=400,



            detail=(



                "Invalid region. Allowed values: "



                "iran, afghanistan"



            )



        )







    asset = db.execute(



        select(Asset)



        .where(



            Asset.symbol == symbol,



            Asset.asset_type == "forex",



            Asset.quote_currency == quote_currency,



            Asset.is_active == True



        )



    ).scalar_one_or_none()







    if not asset:







        raise HTTPException(



            status_code=404,



            detail="FX asset not found"



        )







    market_price = get_latest_market_price(



        db,



        asset



    )







    if not market_price:







        raise HTTPException(



            status_code=404,



            detail="FX price is not available"



        )







    return {
        "category": (
            "iran_fx"
            if region == "iran"
            else "afghanistan_fx"
        ),
        "region": region,
        "symbol": asset.symbol,
        "name": asset.name,
        "quote_currency": asset.quote_currency,
        "source": (
            asset.network
            if asset.quote_currency == "AFN"
            else "Servix"
        ),
        "price": float(market_price.price),
        "change_24h": float(market_price.change_24h),
        "recorded_at": market_price.recorded_at,
    }
