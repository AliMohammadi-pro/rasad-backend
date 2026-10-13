import json

import os

import time

import urllib.error

import urllib.parse

import urllib.request

from html import unescape

import re



from datetime import datetime, timedelta



from dotenv import load_dotenv

from sqlalchemy import select

from sqlalchemy.orm import Session



from app.models.asset import Asset

from app.models.market_price import MarketPrice

from app.models.market_candle import MarketCandle

from app.services.candle_service import (

    upsert_one_minute_candle,

    upsert_external_ohlcv_candle,

    get_candles,

)





# =========================================================

# Environment

# =========================================================



load_dotenv()





# =========================================================

# Configuration

# =========================================================



COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

MARKET_API_URL = (
    f"{COINGECKO_BASE_URL}/simple/price"
)

COINGECKO_MARKET_CHART_URL = (
    f"{COINGECKO_BASE_URL}/coins/{{coin_id}}/market_chart"
)

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

# CoinGecko Demo auto-granularity used by this project:
# 1 day -> 5-minute observations; 7/30/90 days -> hourly;
# 1 year -> daily.
COINGECKO_HISTORY_CONFIG = {
    "24h": {"days": "1", "base_interval": 5},
    "7d": {"days": "7", "base_interval": 60},
    "30d": {"days": "30", "base_interval": 60},
    "90d": {"days": "90", "base_interval": 60},
    "1y": {"days": "365", "base_interval": 1440},
    "all": {"days": "365", "base_interval": 1440},
}

COINGECKO_HISTORY_MIN_CANDLES = 50

def _coingecko_headers() -> dict:
    if not COINGECKO_API_KEY:
        return {}
    return {"x-cg-demo-api-key": COINGECKO_API_KEY}



TWELVE_DATA_URL = (

    "https://api.twelvedata.com/quote"

)



OILPRICEAPI_URL = (

    "https://api.oilpriceapi.com/v1/prices/latest"

)



SERVIX_API_URL = (

    "https://servix.cc/api/v1/assets"

)





TWELVE_DATA_API_KEY = os.getenv(

    "TWELVE_DATA_API_KEY"

)



OILPRICEAPI_KEY = os.getenv(

    "OILPRICEAPI_KEY"

)



SERVIX_API_KEY = os.getenv(

    "SERVIX_API_KEY"

)





# =========================================================

# Gold

# =========================================================



GOLD_SYMBOL = "XAU/USD"





# =========================================================

# Energy / Oil

# =========================================================



# Internal symbols -> OilPriceAPI commodity codes

#

# Brent and WTI are officially documented by OilPriceAPI.

#

# Urals is kept in our database structure, but we do not

# send a guessed provider code for it.

#

# This prevents the API from breaking because of an

# unsupported/incorrect commodity code.

#

OIL_SYMBOLS = {

    "BRENT": "BRENT_CRUDE_USD",

    "WTI": "WTI_USD",

    "URALS": "URALS_CRUDE_USD",

}





# =========================================================

# Request configuration

# =========================================================



REQUEST_TIMEOUT = 20



MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]





# CoinGecko IDs

# =========================================================




COIN_IDS = {

    "1INCH": "1inch",
    "AAVE": "aave",
    "ADA": "cardano",
    "AIOZ": "aioz-network",
    "ALGO": "algorand",
    "APE": "apecoin",
    "APT": "aptos",
    "AR": "arweave",
    "ARB": "arbitrum",
    "ASTR": "astar",
    "ATOM": "cosmos",
    "AVAX": "avalanche-2",
    "AXS": "axie-infinity",
    "BCH": "bitcoin-cash",
    "BLUR": "blur",
    "BNB": "binancecoin",
    "BONK": "bonk",
    "BRETT": "brett",
    "BTC": "bitcoin",
    "CAKE": "pancakeswap-token",
    "CELO": "celo",
    "CHZ": "chiliz",
    "COMP": "compound-governance-token",
    "CRO": "crypto-com-chain",
    "CRV": "curve-dao-token",
    "DAI": "dai",
    "DASH": "dash",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "DYDX": "dydx",
    "EGLD": "elrond-erd-2",
    "ENA": "ethena",
    "ENJ": "enjincoin",
    "EOS": "eos",
    "ETC": "ethereum-classic",
    "ETH": "ethereum",
    "FET": "fetch-ai",
    "FIL": "filecoin",
    "FLOKI": "floki",
    "FLOW": "flow",
    "GALA": "gala",
    "GMX": "gmx",
    "GRAM": "the-open-network",
    "GRT": "the-graph",
    "HBAR": "hedera-hashgraph",
    "HYPE": "hyperliquid",
    "ICP": "internet-computer",
    "ILV": "illuvium",
    "IMX": "immutable-x",
    "INJ": "injective-protocol",
    "IOTA": "iota",
    "IOTX": "iotex",
    "JASMY": "jasmycoin",
    "JTO": "jito-governance-token",
    "JUP": "jupiter-exchange-solana",
    "KAS": "kaspa",
    "KAVA": "kava",
    "KSM": "kusama",
    "LDO": "lido-dao",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "LUNC": "terra-luna",
    "MANA": "decentraland",
    "MINA": "mina-protocol",
    "MKR": "maker",
    "MNT": "mantle",
    "NEAR": "near",
    "NEO": "neo",
    "NOT": "notcoin",
    "OKB": "okb",
    "ONDO": "ondo-finance",
    "ONE": "harmony",
    "OP": "optimism",
    "PENDLE": "pendle",
    "PEPE": "pepe",
    "POL": "matic-network",
    "PYTH": "pyth-network",
    "QNT": "quant-network",
    "RAY": "raydium",
    "RENDER": "render-token",
    "ROSE": "oasis-network",
    "RPL": "rocket-pool",
    "RUNE": "thorchain",
    "SAND": "the-sandbox",
    "SEI": "sei-network",
    "SHIB": "shiba-inu",
    "SNX": "havven",
    "SOL": "solana",
    "STRK": "starknet",
    "STX": "blockstack",
    "SUI": "sui",
    "SUSHI": "sushi",
    "TAO": "bittensor",
    "THETA": "theta-token",
    "TIA": "celestia",
    "TON": "the-open-network",
    "TRUMP": "official-trump",
    "TRX": "tron",
    "TURBO": "turbo",
    "UNI": "uniswap",
    "USDC": "usd-coin",
    "USDT": "tether",
    "VET": "vechain",
    "WIF": "dogwifcoin",
    "WLD": "worldcoin",
    "XDC": "xdce-crowd-sale",
    "XLM": "stellar",
    "XMR": "monero",
    "XRP": "ripple",
    "XTZ": "tezos",
    "ZEC": "zcash",
    "ZK": "zksync",
}





# =========================================================

# Generic HTTP JSON request

# =========================================================



def make_request(

    url: str,

    headers: dict | None = None,

    retries: int = MAX_RETRIES

) -> dict:



    last_error = None



    request_headers = {

        "User-Agent": "CryptoMarket/1.0",

        "Accept": "application/json",

    }



    if headers:

        request_headers.update(headers)



    for attempt in range(retries):



        request = urllib.request.Request(

            url,

            headers=request_headers

        )



        try:



            with urllib.request.urlopen(

                request,

                timeout=REQUEST_TIMEOUT

            ) as response:



                raw_data = response.read().decode(

                    "utf-8"

                )



                data = json.loads(

                    raw_data

                )



                return data



        except urllib.error.HTTPError as e:



            last_error = e



            # -----------------------------------------

            # Rate limit

            # -----------------------------------------



            if e.code == 429:



                retry_after = e.headers.get(

                    "Retry-After"

                )



                if retry_after:



                    try:



                        delay = float(

                            retry_after

                        )



                    except ValueError:



                        delay = RETRY_DELAYS[

                            min(

                                attempt,

                                len(RETRY_DELAYS) - 1

                            )

                        ]



                else:



                    delay = RETRY_DELAYS[

                        min(

                            attempt,

                            len(RETRY_DELAYS) - 1

                        )

                    ]



                print(

                    f"[Market] Rate limit (429). "

                    f"Retrying in {delay}s..."

                )



                if attempt < retries - 1:



                    time.sleep(

                        delay

                    )



                    continue



                raise RuntimeError(

                    "Market API rate limit exceeded "

                    "after multiple retries."

                )



            # -----------------------------------------

            # Temporary server errors

            # -----------------------------------------



            if e.code in (

                500,

                502,

                503,

                504

            ):



                delay = RETRY_DELAYS[

                    min(

                        attempt,

                        len(RETRY_DELAYS) - 1

                    )

                ]



                print(

                    f"[Market] HTTP {e.code}. "

                    f"Retrying in {delay}s..."

                )



                if attempt < retries - 1:



                    time.sleep(

                        delay

                    )



                    continue



                raise RuntimeError(

                    f"Market API server error: "

                    f"HTTP {e.code}"

                )



            # -----------------------------------------

            # Permanent HTTP errors

            # -----------------------------------------



            try:



                error_body = e.read().decode(

                    "utf-8"

                )



            except Exception:



                error_body = ""



            raise RuntimeError(

                f"Market API HTTP {e.code}: "

                f"{error_body}"

            )



        except urllib.error.URLError as e:



            last_error = e



            delay = RETRY_DELAYS[

                min(

                    attempt,

                    len(RETRY_DELAYS) - 1

                )

            ]



            print(

                f"[Market] Network error: {e}. "

                f"Retrying in {delay}s..."

            )



            if attempt < retries - 1:



                time.sleep(

                    delay

                )



                continue



            raise RuntimeError(

                f"Market API network error: {e}"

            )



        except TimeoutError as e:



            last_error = e



            delay = RETRY_DELAYS[

                min(

                    attempt,

                    len(RETRY_DELAYS) - 1

                )

            ]



            print(

                f"[Market] Timeout. "

                f"Retrying in {delay}s..."

            )



            if attempt < retries - 1:



                time.sleep(

                    delay

                )



                continue



            raise RuntimeError(

                "Market API request timed out."

            )



        except http.client.IncompleteRead as e:
            last_error = e
            delay = RETRY_DELAYS[
                min(
                    attempt,
                    len(RETRY_DELAYS) - 1
                )
            ]
            print(
                f"[Market] Incomplete response from API. "
                f"Retrying in {delay}s..."
            )
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise RuntimeError(
                f"Market API incomplete response: {e}"
            )

        except json.JSONDecodeError as e:



            raise RuntimeError(

                f"Invalid JSON response "

                f"from market API: {e}"

            )



        except Exception as e:



            raise RuntimeError(

                f"Unexpected market API error: {e}"

            )



    raise RuntimeError(

        f"Market API request failed: {last_error}"

    )





# =========================================================

# Crypto prices

# =========================================================






def ensure_coingecko_history(
    db: Session,
    asset: Asset,
    period: str,
) -> int:
    """Fetch/persist only the selected crypto history when needed."""
    if asset.asset_type != "crypto":
        raise ValueError(
            "Technical analysis is available only for crypto assets."
        )

    period = period.lower().strip()
    config = COINGECKO_HISTORY_CONFIG.get(period)
    durations = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
        "all": timedelta(days=365),
    }
    if config is None or period not in durations:
        raise ValueError(
            "Invalid CoinGecko history period. Allowed values: "
            + ", ".join(COINGECKO_HISTORY_CONFIG.keys())
        )

    now = datetime.utcnow()
    start_time = now - durations[period]
    base_interval = config["base_interval"]

    rows = db.execute(
        select(MarketCandle)
        .where(
            MarketCandle.asset_id == asset.id,
            MarketCandle.interval_minutes == base_interval,
        )
        .order_by(MarketCandle.recorded_at.asc())
    ).scalars().all()

    tolerance = timedelta(minutes=max(base_interval * 3, 15))
    covered = (
        len(rows) >= COINGECKO_HISTORY_MIN_CANDLES
        and rows[0].recorded_at <= start_time + tolerance
        and rows[-1].recorded_at >= now - tolerance
    )
    if covered:
        return 0

    candles = get_coingecko_historical_candles(asset.symbol, period)
    saved = 0
    for candle in candles:
        upsert_external_ohlcv_candle(
            db,
            asset,
            recorded_at=datetime.fromisoformat(candle["timestamp"]),
            open_price=candle["open"],
            high_price=candle["high"],
            low_price=candle["low"],
            close_price=candle["close"],
            volume=None,
            interval_minutes=base_interval,
        )
        saved += 1

    db.commit()
    print(
        f"[History] CoinGecko history saved: "
        f"{asset.symbol} / {period} -> {saved} candles"
    )
    return saved


def get_crypto_prices(
    symbols: list[str] | None = None
) -> dict:
    """Fetch all configured crypto prices from CoinGecko.

    The configured list is the source of truth. The batch request is followed
    by a one-ID recovery request for any symbol omitted from the batch result.
    This prevents one transient/missing response from silently reducing the
    number of updated assets.
    """
    if symbols is None:
        symbols = list(COIN_IDS.keys())

    normalized_symbols = [s.upper() for s in symbols]
    coin_ids = [COIN_IDS[s] for s in normalized_symbols if COIN_IDS.get(s)]
    if not coin_ids:
        return {}

    # Avoid duplicate IDs (GRAM and TON currently resolve to the same
    # CoinGecko asset) while keeping both symbols in the result.
    unique_coin_ids = list(dict.fromkeys(coin_ids))

    params = {
        "ids": ",".join(unique_coin_ids),
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }

    url = f"{MARKET_API_URL}?{urllib.parse.urlencode(params)}"
    data = make_request(url, headers=_coingecko_headers())
    if not isinstance(data, dict):
        data = {}

    result = {}

    def add_result(symbol: str, coin_data: dict | None) -> None:
        if not isinstance(coin_data, dict):
            return
        price = coin_data.get("usd")
        if price is None:
            return
        result[symbol] = {
            "price": price,
            "change_24h": coin_data.get("usd_24h_change", 0) or 0,
            "volume_24h": coin_data.get("usd_24h_vol"),
            "market_cap": coin_data.get("usd_market_cap"),
        }

    # First pass: batch response.
    for symbol in normalized_symbols:
        coin_id = COIN_IDS.get(symbol)
        if coin_id:
            add_result(symbol, data.get(coin_id))

    # Second pass: recover anything omitted by the batch response.
    missing_symbols = [
        symbol for symbol in normalized_symbols
        if symbol not in result and COIN_IDS.get(symbol)
    ]

    for symbol in missing_symbols:
        coin_id = COIN_IDS[symbol]
        single_params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_market_cap": "true",
        }
        try:
            single_url = f"{MARKET_API_URL}?{urllib.parse.urlencode(single_params)}"
            single_data = make_request(
                single_url,
                headers=_coingecko_headers(),
                retries=2,
            )
            add_result(
                symbol,
                single_data.get(coin_id) if isinstance(single_data, dict) else None,
            )
        except Exception as e:
            print(f"[Market] CoinGecko fallback failed for {symbol}: {e}")

    still_missing = [
        symbol for symbol in normalized_symbols
        if symbol not in result and COIN_IDS.get(symbol)
    ]
    if still_missing:
        print(
            "[Market] CoinGecko missing symbols: "
            + ", ".join(still_missing)
        )

    return result


# =========================================================
# Afghanistan Gold - Herat Goldsmiths Union Telegram
# =========================================================



# Public TG.ME mirror of the Herat Gold / exchange-rate Telegram channel.

# The source publishes several local Herat gold/coin prices, but not every

# post contains every item. We only return values that are actually found.

HERAT_GOLD_TELEGRAM_URL = "https://tg.me/herat_gold"



_herat_gold_cache = {

    "data": None,

    "fetched_at": 0.0,

}



HERAT_GOLD_CACHE_SECONDS = 90





def _strip_html_tags(value: str) -> str:

    """

    Convert the TG.ME HTML page to readable text.



    Newlines are intentionally preserved around common block elements so

    separate Telegram posts do not get accidentally merged together.

    """

    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)

    value = re.sub(

        r"</(?:p|div|li|tr|td|th|section|article|h[1-6])>",

        "\n",

        value,

        flags=re.I,

    )

    value = re.sub(r"<[^>]+>", " ", value)

    value = unescape(value)

    value = re.sub(r"[ \t\r\f\v]+", " ", value)

    value = re.sub(r"\n[ \t]+", "\n", value)

    return value.strip()





def _herat_digits(value: str) -> str:

    return (value or "").translate(

        str.maketrans(

            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",

            "01234567890123456789",

        )

    )





def _herat_number(value: str):

    value = _herat_digits(value)

    value = value.replace(",", "").replace("،", "").replace("٬", "")

    value = value.replace("؋", "").replace("$", "").strip()



    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:

        return None



    try:

        number = float(match.group(0))

    except ValueError:

        return None



    # Prices are AFN/gram or AFN/coin and therefore must be positive.

    return number if number > 0 else None





def _herat_buy_sell(text: str):

    """

    Parse a single buy/sell pair from one logical source block.



    Accepted examples:

        خرید: 6610؋

        فروش: 6640؋

        خرید ۶۶۱۰

        فروش ۶۶۴۰



    The parser never invents a value. Both buy and sell must exist.

    """

    buy_match = re.search(

        r"خ(?:ـ)?رید\s*[:：-]?\s*[`'\"“”«»\s]*"

        r"([0-9۰-۹٠-٩][0-9۰-۹٠-٩,،٬.]*)",

        text,

        flags=re.I,

    )



    if not buy_match:

        return None



    sell_match = re.search(

        r"ف(?:ـ)?روش\s*[:：-]?\s*[`'\"“”«»\s]*"

        r"([0-9۰-۹٠-٩][0-9۰-۹٠-٩,،٬.]*)",

        text[buy_match.end():],

        flags=re.I,

    )



    if not sell_match:

        return None



    buy = _herat_number(buy_match.group(1))

    sell = _herat_number(sell_match.group(1))



    if buy is None or sell is None:

        return None



    return {

        "buy": buy,

        "sell": sell,

        "price": (buy + sell) / 2,

    }





def _herat_extract_after_label(

    text: str,

    label_pattern: str,

    max_chars: int = 350,

):

    """

    Find a specific item label and parse only the nearby text.



    Keeping the window small prevents a buy/sell pair belonging to another

    gold type or another Telegram post from being incorrectly attached.

    """

    normalized = _herat_digits(text)



    for match in re.finditer(

        label_pattern,

        normalized,

        flags=re.I,

    ):

        window = normalized[

            match.end():match.end() + max_chars

        ]



        # Stop at another known item heading when possible.

        next_heading = re.search(

            r"(?:هر\s+گرام\s+طلای|طلای\s+\d+\s+عیار|"

            r"سکه\s+(?:ربع|نیم|کامل)|"

            r"فی\s+گرام\s+طلای\s+آبشده)",

            window,

            flags=re.I,

        )

        if next_heading:

            window = window[:next_heading.start()]



        rate = _herat_buy_sell(window)

        if rate:

            return rate



    return None





def _herat_extract_18k(text: str):

    # Prefer the explicit daily/local-gold form.

    rate = _herat_extract_after_label(

        text,

        r"(?:هر\s+گرام\s+)?طلای\s*18\s*عیار",

    )

    if rate:

        return rate



    # Also supports the live "قیمت لحظه‌ای طلای 18 عیار" posts.

    return _herat_extract_after_label(

        text,

        r"طلای\s*18",

    )





def _herat_extract_21k(text: str):

    return _herat_extract_after_label(

        text,

        r"(?:هر\s+گرام\s+)?طلای\s*21\s*عیار",

    )





def _herat_extract_coin(text: str, coin_name: str):

    return _herat_extract_after_label(

        text,

        rf"سکه\s+{coin_name}",

        max_chars=220,

    )





def _herat_extract_melted(text: str):

    return _herat_extract_after_label(

        text,

        r"(?:فی\s+گرام\s+)?طلای\s+آبشده(?:\s+بدون\s+اجرت)?",

        max_chars=250,

    )





def _herat_message_blocks(html: str) -> list[str]:

    """

    Return individual Telegram message texts when TG.ME exposes them.



    The current TG.ME page can also expose a rendered text structure that

    does not use Telegram's old HTML class, so callers additionally use

    the complete page text as a fallback.

    """

    blocks = re.findall(

        r'<div[^>]*class="[^"]*tgme_widget_message_text[^"]*"[^>]*>'

        r"(.*?)</div>",

        html,

        flags=re.I | re.S,

    )



    return [

        _strip_html_tags(block)

        for block in blocks

        if _strip_html_tags(block)

    ]





def _herat_rate_from_blocks(

    blocks: list[str],

    extractor,

):

    """

    Try newest-to-oldest message blocks first.

    TG.ME exposes newest posts first.

    """

    for block in blocks:

        rate = extractor(block)

        if rate:

            return rate



    return None





def get_cached_herat_gold_price() -> dict | None:
    return _herat_gold_cache.get("data")


def herat_gold_cache_is_fresh() -> bool:
    cached = _herat_gold_cache.get("data")
    if not cached:
        return False
    return (
        time.time() - _herat_gold_cache.get("fetched_at", 0.0)
        < HERAT_GOLD_CACHE_SECONDS
    )


def get_herat_gold_price() -> dict:

    """

    Get all Herat gold/coin prices that are actually published by the

    source and can be parsed reliably.



    Possible source items currently include:

      - 18K gold / gram

      - 21K gold / gram

      - quarter coin

      - half coin

      - full coin

      - melted gold without making charge



    Important:

      We do NOT calculate missing source prices and do NOT return fake

      placeholders/null entries for products that were not published.

    """



    now = time.time()

    cached = _herat_gold_cache.get("data")



    if (

        cached

        and now - _herat_gold_cache["fetched_at"]

        < HERAT_GOLD_CACHE_SECONDS

    ):

        return cached



    html = _make_text_request(

        HERAT_GOLD_TELEGRAM_URL

    )



    # Try individual Telegram posts first.

    blocks = _herat_message_blocks(html)



    # Current TG.ME also has a rendered page format without the old

    # tgme_widget_message_text class. Keep the full text as a fallback.

    full_text = _strip_html_tags(html)



    if full_text:

        # The full page is useful for the current format. It is deliberately

        # added after individual blocks so a structured message wins.

        blocks_with_fallback = blocks + [full_text]

    else:

        blocks_with_fallback = blocks



    if not blocks_with_fallback:

        raise RuntimeError(

            "Herat gold source returned no readable content."

        )



    # ---------------------------------------------------------

    # Extract each product independently.

    # ---------------------------------------------------------

    # This is important because:

    #   - live posts may contain only 18K;

    #   - daily posts contain 18K + 21K + coins;

    #   - melted-gold price can be published in a separate post.

    #

    # Therefore we must not require all products to exist in one post.

    rate_18k = _herat_rate_from_blocks(

        blocks_with_fallback,

        _herat_extract_18k,

    )



    rate_21k = _herat_rate_from_blocks(

        blocks_with_fallback,

        _herat_extract_21k,

    )



    rate_quarter = _herat_rate_from_blocks(

        blocks_with_fallback,

        lambda block: _herat_extract_coin(

            block,

            "ربع",

        ),

    )



    rate_half = _herat_rate_from_blocks(

        blocks_with_fallback,

        lambda block: _herat_extract_coin(

            block,

            "نیم",

        ),

    )



    rate_full = _herat_rate_from_blocks(

        blocks_with_fallback,

        lambda block: _herat_extract_coin(

            block,

            "کامل",

        ),

    )



    rate_melted = _herat_rate_from_blocks(

        blocks_with_fallback,

        _herat_extract_melted,

    )



    if not any(

        (

            rate_18k,

            rate_21k,

            rate_quarter,

            rate_half,

            rate_full,

            rate_melted,

        )

    ):

        raise RuntimeError(

            "No reliable Herat gold/coin prices could be parsed from "

            "https://tg.me/herat_gold."

        )



    # ---------------------------------------------------------

    # Build only the values actually found.

    # ---------------------------------------------------------

    gold = {}

    available_purities = []



    if rate_18k:

        gold["18K"] = {

            "buy": rate_18k["buy"],

            "sell": rate_18k["sell"],

            "price": rate_18k["price"],

            "unit": "AFN/gram",

        }

        available_purities.append("18K")



    if rate_21k:

        gold["21K"] = {

            "buy": rate_21k["buy"],

            "sell": rate_21k["sell"],

            "price": rate_21k["price"],

            "unit": "AFN/gram",

        }

        available_purities.append("21K")



    coins = {}



    if rate_quarter:

        coins["quarter"] = {

            "buy": rate_quarter["buy"],

            "sell": rate_quarter["sell"],

            "price": rate_quarter["price"],

            "unit": "AFN/coin",

        }



    if rate_half:

        coins["half"] = {

            "buy": rate_half["buy"],

            "sell": rate_half["sell"],

            "price": rate_half["price"],

            "unit": "AFN/coin",

        }



    if rate_full:

        coins["full"] = {

            "buy": rate_full["buy"],

            "sell": rate_full["sell"],

            "price": rate_full["price"],

            "unit": "AFN/coin",

        }



    data = {

        "city": "Herat",

        "currency": "AFN",

        "source": (

            "نرخ طلا و اسعار هرات / "

            "منبع اعلام‌شده: اتحادیه زرگران ولایت هرات"

        ),

        "source_url": HERAT_GOLD_TELEGRAM_URL,

        "updated_at": datetime.utcnow().isoformat(),

        "available_purities": available_purities,

        "gold": gold,

        "coins": coins,

    }



    if rate_melted:

        data["melted_gold"] = {

            "buy": rate_melted["buy"],

            "sell": rate_melted["sell"],

            "price": rate_melted["price"],

            "unit": "AFN/gram",

            "name": "طلای آبشده بدون اجرت",

        }



    # Backward compatibility with the frontend/backend code that currently

    # expects the primary Herat value at the top level.

    primary = rate_18k or rate_21k



    if primary:

        data["buy"] = primary["buy"]

        data["sell"] = primary["sell"]

        data["price"] = primary["price"]

        data["unit"] = "AFN/gram"

        data["purity"] = "18K" if rate_18k else "21K"



    _herat_gold_cache["data"] = data

    _herat_gold_cache["fetched_at"] = now



    found_items = []



    if rate_18k:

        found_items.append("18K")

    if rate_21k:

        found_items.append("21K")

    if rate_quarter:

        found_items.append("quarter")

    if rate_half:

        found_items.append("half")

    if rate_full:

        found_items.append("full")

    if rate_melted:

        found_items.append("melted")



    print(

        "[Market] Herat gold updated: "

        + ", ".join(found_items)

    )



    return data





# =========================================================

# Gold - XAU/USD

# =========================================================



def get_gold_price() -> dict:



    if not TWELVE_DATA_API_KEY:



        raise RuntimeError(

            "TWELVE_DATA_API_KEY is not set."

        )



    params = {



        "symbol": GOLD_SYMBOL,



        "apikey": TWELVE_DATA_API_KEY,

    }



    query_string = urllib.parse.urlencode(

        params

    )



    url = (

        f"{TWELVE_DATA_URL}"

        f"?{query_string}"

    )



    data = make_request(

        url

    )



    # Twelve Data can return an error

    # inside the JSON response.



    if data.get("status") == "error":



        raise RuntimeError(

            data.get(

                "message",

                "Twelve Data returned an error."

            )

        )



    price = data.get(

        "close"

    )



    if price is None:



        raise RuntimeError(

            f"Gold price was not returned: {data}"

        )



    try:



        price = float(

            price

        )



    except (

        TypeError,

        ValueError

    ):



        raise RuntimeError(

            f"Invalid gold price: {price}"

        )



    percent_change = data.get(

        "percent_change",

        0

    )



    try:



        percent_change = float(

            percent_change

        )



    except (

        TypeError,

        ValueError

    ):



        percent_change = 0



    return {



        "price": price,



        "change_24h": percent_change,



        "volume_24h": None,



        "market_cap": None,

    }





# =========================================================

# OilPriceAPI helper

# =========================================================



def get_oil_price_by_code(

    provider_code: str

) -> dict:



    if not OILPRICEAPI_KEY:



        raise RuntimeError(

            "OILPRICEAPI_KEY is not set."

        )



    params = {



        "by_code": provider_code

    }



    query_string = urllib.parse.urlencode(

        params

    )



    url = (

        f"{OILPRICEAPI_URL}"

        f"?{query_string}"

    )



    data = make_request(

        url,

        headers={

            "Authorization": (

                f"Token {OILPRICEAPI_KEY}"

            )

        }

    )



    # -----------------------------------------

    # API status

    # -----------------------------------------



    if data.get("status") != "success":



        raise RuntimeError(

            data.get(

                "message",

                "OilPriceAPI returned an error."

            )

        )



    price_data = data.get(

        "data"

    )



    if not isinstance(

        price_data,

        dict

    ):



        raise RuntimeError(

            "Invalid OilPriceAPI response."

        )



    # -----------------------------------------

    # Validate returned code

    # -----------------------------------------



    returned_code = price_data.get(

        "code"

    )



    if returned_code:



        if returned_code.upper() != provider_code.upper():



            raise RuntimeError(

                "OilPriceAPI returned a different "

                "commodity code."

            )



    # -----------------------------------------

    # Price

    # -----------------------------------------



    price = price_data.get(

        "price"

    )



    if price is None:



        raise RuntimeError(

            "OilPriceAPI did not return a price."

        )



    try:



        price = float(

            price

        )



    except (

        TypeError,

        ValueError

    ):



        raise RuntimeError(

            f"Invalid oil price: {price}"

        )



    if price <= 0:



        raise RuntimeError(

            f"Invalid oil price value: {price}"

        )



    # -----------------------------------------

    # Change

    # -----------------------------------------

    #

    # OilPriceAPI's latest endpoint does not

    # necessarily expose a 24h percentage field

    # in the same format as Twelve Data.

    #

    # Therefore we safely use 0 here.

    #

    # Later we can calculate the change from

    # our own stored prices.

    #



    percent_change = 0



    return {



        "price": price,



        "change_24h": percent_change,



        "volume_24h": None,



        "market_cap": None,

    }





# =========================================================

# Energy / Oil prices

# =========================================================



def get_energy_prices() -> dict:

    """

    Get current prices for major crude oil benchmarks.



    Current provider:

        OilPriceAPI



    Supported provider codes:

        BRENT_CRUDE_USD

        WTI_USD



    Internal symbols:

        BRENT

        WTI



    URALS remains in the database but is not requested

    until a verified OilPriceAPI commodity code is used.

    """



    if not OILPRICEAPI_KEY:



        raise RuntimeError(

            "OILPRICEAPI_KEY is not set."

        )



    result = {}



    for (

        internal_symbol,

        provider_code

    ) in OIL_SYMBOLS.items():



        try:



            oil_price = (

                get_oil_price_by_code(

                    provider_code

                )

            )



            result[internal_symbol] = (

                oil_price

            )



            print(

                f"[Market] "

                f"Oil updated: "

                f"{internal_symbol} = "

                f"{oil_price['price']}"

            )



        except Exception as error:



            print(

                f"[Market] "

                f"Oil update failed for "

                f"{internal_symbol}: "

                f"{error}"

            )



    return result







# =========================================================

# Iran / Afghanistan FX

# =========================================================



# Iran FX continues to use Servix.

# Afghanistan FX uses Khorasan Market for the local market pairs,

# while Indian Rupee / Afghan Afghani is taken directly from

# Da Afghanistan Bank (DAB).

#

# Khorasan source:

#   https://sarafi.af/fa/exchange-rates/khorasan-market

#

# Official DAB source:

#   https://dab.gov.af/exchange-rates



KHORASAN_RATES_URL = (

    "https://sarafi.af/fa/exchange-rates/khorasan-market"

)


SARAI_SHAHZADA_RATES_URL = (

    "https://sarafi.af/fa/exchange-rates/sarai-shahzada"

)



DAB_RATES_URLS = (
    "https://www.dab.gov.af/exchange-rates",
    "https://dab.gov.af/exchange-rates",
)





# ---------------------------------------------------------

# Servix FX configuration (Iran)

# ---------------------------------------------------------



SERVIX_FX_CODES = [

    "USD_RLS",

    "EUR_RLS",

    "CNY_RLS",

    "RUB_RLS",



    "GBP_USD",

    "AED_USD",

    "TRY_USD",

    "INR_USD",

    "CAD_USD",

    "AUD_USD",



    "AFN_USD",

    "IQD_USD",

    "PKR_USD",

]





def _to_float(value, code: str) -> float:

    try:

        result = float(value)

    except (TypeError, ValueError):

        raise RuntimeError(

            f"Invalid Servix value for {code}: {value}"

        )



    if result <= 0:

        raise RuntimeError(

            f"Invalid Servix value for {code}: {result}"

        )



    return result





def get_servix_fx_data() -> dict:

    """

    Fetch all required Iran FX rates from Servix in one request.

    """



    if not SERVIX_API_KEY:

        raise RuntimeError(

            "SERVIX_API_KEY is not set."

        )



    params = {

        "codes": ",".join(SERVIX_FX_CODES)

    }



    query_string = urllib.parse.urlencode(

        params

    )



    url = (

        f"{SERVIX_API_URL}"

        f"?{query_string}"

    )



    data = make_request(

        url,

        headers={

            "X-API-Key": SERVIX_API_KEY

        }

    )



    if not isinstance(data, list):

        raise RuntimeError(

            f"Invalid Servix response: {data}"

        )



    result = {}



    for item in data:



        if not isinstance(item, dict):

            continue



        code = item.get("code")



        if not code:

            continue



        value = item.get("value")



        if value is None:

            continue



        result[code.upper()] = _to_float(

            value,

            code

        )



    if not result:

        raise RuntimeError(

            "Servix returned no FX prices."

        )



    return result





def _fx_result(price: float) -> dict:

    return {

        "price": price,

        "change_24h": 0,

        "volume_24h": None,

        "market_cap": None,

    }





def get_iran_fx_prices() -> dict:

    """

    Iranian Toman display prices from Servix.

    """



    rates = get_servix_fx_data()



    usd_rls = rates.get("USD_RLS")

    eur_rls = rates.get("EUR_RLS")

    cny_rls = rates.get("CNY_RLS")

    rub_rls = rates.get("RUB_RLS")



    if usd_rls is None:

        raise RuntimeError(

            "Servix did not return USD_RLS."

        )



    result = {

        "USD_IRT": _fx_result(

            usd_rls / 10

        ),

    }



    if eur_rls is not None:

        result["EUR_IRT"] = _fx_result(

            eur_rls / 10

        )



    usd_pairs = {

        "GBP_IRT": "GBP_USD",

        "AED_IRT": "AED_USD",

        "TRY_IRT": "TRY_USD",

        "INR_IRT": "INR_USD",

        "CAD_IRT": "CAD_USD",

        "AUD_IRT": "AUD_USD",

        "AFN_IRT": "AFN_USD",

        "IQD_IRT": "IQD_USD",

    }



    for internal_symbol, provider_code in usd_pairs.items():



        rate = rates.get(provider_code)



        if rate is None:

            continue



        result[internal_symbol] = _fx_result(

            rate * usd_rls / 10

        )



    if cny_rls is not None:

        result["CNY_IRT"] = _fx_result(

            cny_rls / 10

        )



    if rub_rls is not None:

        result["RUB_IRT"] = _fx_result(

            rub_rls / 10

        )



    return result





# ---------------------------------------------------------

# Khorasan Market HTML parser

# ---------------------------------------------------------



from html.parser import HTMLParser





class _KhorasanTableParser(HTMLParser):

    """

    Small dependency-free HTML table parser.

    """



    def __init__(self):

        super().__init__()

        self.rows = []

        self._row = None

        self._cell = None

        self._cell_tag = None



    def handle_starttag(self, tag, attrs):

        tag = tag.lower()



        if tag == "tr":

            self._row = []



        elif tag in ("td", "th") and self._row is not None:

            self._cell = []

            self._cell_tag = tag



    def handle_data(self, data):

        if self._cell is not None:

            self._cell.append(data)



    def handle_endtag(self, tag):

        tag = tag.lower()



        if tag in ("td", "th") and self._cell is not None:

            value = " ".join(

                "".join(self._cell).split()

            )



            self._row.append(value)

            self._cell = None

            self._cell_tag = None



        elif tag == "tr" and self._row is not None:

            if self._row:

                self.rows.append(self._row)



            self._row = None





def _make_text_request(url: str) -> str:

    """

    Download HTML text with the same basic retry policy used

    by the JSON market requests.

    """



    last_error = None



    headers = {

        "User-Agent": "Mozilla/5.0 (CryptoMarket/1.0)",

        "Accept": "text/html,application/xhtml+xml",

    }



    for attempt in range(MAX_RETRIES):



        request = urllib.request.Request(

            url,

            headers=headers

        )



        try:



            with urllib.request.urlopen(

                request,

                timeout=REQUEST_TIMEOUT

            ) as response:



                charset = response.headers.get_content_charset()

                raw_data = response.read()



                return raw_data.decode(

                    charset or "utf-8",

                    errors="replace"

                )



        except urllib.error.HTTPError as error:



            last_error = error



            if error.code in (

                429,

                500,

                502,

                503,

                504

            ):



                delay = RETRY_DELAYS[

                    min(

                        attempt,

                        len(RETRY_DELAYS) - 1

                    )

                ]



                print(

                    f"[Market] HTML source HTTP "

                    f"{error.code}. Retrying in {delay}s..."

                )



                if attempt < MAX_RETRIES - 1:

                    time.sleep(delay)

                    continue



            raise RuntimeError(

                f"Khorasan source HTTP error: {error.code}"

            )



        except (

            urllib.error.URLError,

            TimeoutError

        ) as error:



            last_error = error



            delay = RETRY_DELAYS[

                min(

                    attempt,

                    len(RETRY_DELAYS) - 1

                )

            ]



            print(

                f"[Market] HTML source network error. "

                f"Retrying in {delay}s..."

            )



            if attempt < MAX_RETRIES - 1:

                time.sleep(delay)

                continue



        except Exception as error:

            raise RuntimeError(

                f"HTML source error: {error}"

            )



    raise RuntimeError(

        f"HTML source request failed: {last_error}"

    )







# =========================================================

# Iran local gold + silver - TGJU public market page

# =========================================================



TGJU_LOCAL_MARKETS_URL = (

    "https://www.tgju.org/local-markets"

)



TGJU_COIN_URL = (

    "https://www.tgju.org/coin"

)



TGJU_LOCAL_METALS_CACHE_SECONDS = 30


TGJU_LOCAL_METALS_CACHE_FILE = os.path.join(
    os.path.dirname(__file__),
    ".iran_local_metals_cache.json"
)


_tgju_local_metals_cache = {

    "data": None,

    "fetched_at": 0.0,

}





class _TGJUMarketTableParser(HTMLParser):

    """Dependency-free parser for TGJU local-market tables."""



    def __init__(self):

        super().__init__()

        self.rows = []

        self._row = None

        self._cell = None



    def handle_starttag(self, tag, attrs):

        tag = tag.lower()



        if tag == "tr":

            self._row = []



        elif tag in ("td", "th") and self._row is not None:

            self._cell = []



    def handle_data(self, data):

        if self._cell is not None:

            self._cell.append(data)



    def handle_endtag(self, tag):

        tag = tag.lower()



        if tag in ("td", "th") and self._cell is not None:

            value = " ".join("".join(self._cell).split())

            self._row.append(value)

            self._cell = None



        elif tag == "tr" and self._row is not None:

            if self._row:

                self.rows.append(self._row)

            self._row = None





def _tgju_digits(value: str) -> str:

    return value.translate(

        str.maketrans(

            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",

            "01234567890123456789"

        )

    )





def _tgju_number(value: str):

    value = _tgju_digits(value or "")

    value = value.replace(",", "").replace("،", "")

    value = value.replace("٬", "").strip()



    match = re.search(r"[-+]?\d+(?:.\d+)?", value)

    if not match:

        return None



    try:

        number = float(match.group(0))

    except ValueError:

        return None



    return number





def _tgju_row_percent(row: list[str]) -> float:

    """Extract the first percentage from a TGJU market row."""

    for cell in row[2:]:

        normalized = _tgju_digits(cell)

        match = re.search(r"\(?([+-]?\d+(?:.\d+)?)%?\)?", normalized)

        if match:

            try:

                return float(match.group(1))

            except ValueError:

                pass

    return 0.0





def _tgju_find_row(rows: list[list[str]], labels: tuple[str, ...]):

    for row in rows:

        if not row:

            continue



        label = " ".join(row[0].split())

        normalized = _tgju_digits(label)



        for wanted in labels:

            if wanted in normalized:

                return row



    return None





def _tgju_find_rows(rows: list[list[str]], labels: tuple[str, ...]):

    matches = []



    for row in rows:

        if not row:

            continue



        label = " ".join(row[0].split())

        normalized = _tgju_digits(label)



        if any(wanted in normalized for wanted in labels):

            matches.append(row)



    return matches





def _tgju_parse_local_metals(html: str) -> dict:

    parser = _TGJUMarketTableParser()

    parser.feed(html)



    definitions = [

        (

            "GOLD18_IRT",

            "طلای 18 عیار",

            ("طلای 18 عیار", "طلای 18 عیار / 750"),

            "18K",

            "gram",

        ),

        (

            "GOLD24_IRT",

            "طلای 24 عیار",

            ("طلای 24 عیار",),

            "24K",

            "gram",

        ),

        (

            "GOLD_USED_IRT",

            "طلای دست دوم",

            ("طلای دست دوم",),

            "Used",

            "gram",

        ),

        (

            "MESGHAL_IRT",

            "مثقال طلا",

            ("مثقال طلا",),

            "Mesghal",

            "mesghal",

        ),

        (

            "SILVER999_IRT",

            "گرم نقره 999",

            ("گرم نقره 999", "نقره 999"),

            "999",

            "gram",

        ),

        (

            "SILVER925_IRT",

            "گرم نقره 925",

            ("گرم نقره 925", "نقره 925"),

            "925",

            "gram",

        ),

    ]



    result = []



    for symbol, name, labels, purity, unit in definitions:

        row = _tgju_find_row(parser.rows, labels)



        if not row or len(row) < 2:

            continue



        price = _tgju_number(row[1])



        if price is None or price <= 0:

            continue



        result.append(

            {

                "symbol": symbol,

                "name": name,

                "purity": purity,

                "unit": unit,

                "price": price / 10,

                "change_24h": _tgju_row_percent(row),

                "currency": "IRT",

            }

        )



    return result





def _tgju_parse_coins(html: str) -> list[dict]:

    parser = _TGJUMarketTableParser()

    parser.feed(html)



    definitions = [

        ("COIN_EMAMI_IRT", "سکه امامی", ("سکه امامی",)),

        ("COIN_BAHAR_IRT", "سکه بهار آزادی", ("سکه بهار آزادی",)),

        ("COIN_HALF_IRT", "نیم سکه", ("نیم سکه",)),

        ("COIN_QUARTER_IRT", "ربع سکه", ("ربع سکه",)),

        ("COIN_GRAMI_IRT", "سکه گرمی", ("سکه گرمی",)),

    ]



    result = []



    for symbol, name, labels in definitions:

        rows = _tgju_find_rows(parser.rows, labels)



        # /coin contains, in order, نقدی, تک فروشی and حباب rows.

        cash_row = rows[0] if len(rows) >= 1 else None

        retail_row = rows[1] if len(rows) >= 2 else None

        bubble_row = rows[2] if len(rows) >= 3 else None



        if not cash_row or len(cash_row) < 2:

            continue



        cash = _tgju_number(cash_row[1])

        if cash is None or cash <= 0:

            continue



        item = {

            "symbol": symbol,

            "name": name,

            "unit": "coin",

            "price": cash / 10,

            "change_24h": _tgju_row_percent(cash_row),

            "currency": "IRT",

        }



        if retail_row and len(retail_row) >= 2:

            retail = _tgju_number(retail_row[1])

            if retail and retail > 0:

                item["retail_price"] = retail / 10



        if bubble_row and len(bubble_row) >= 2:

            bubble = _tgju_number(bubble_row[1])

            if bubble is not None and bubble >= 0:

                item["bubble"] = bubble / 10



        result.append(item)



    return result





def _load_persistent_iran_metals_cache() -> dict | None:
    """Load the last successful TGJU response from disk."""
    try:
        if not os.path.exists(TGJU_LOCAL_METALS_CACHE_FILE):
            return None

        with open(
            TGJU_LOCAL_METALS_CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            cached = json.load(file)

        if (
            isinstance(cached, dict)
            and isinstance(cached.get("data"), list)
            and cached.get("data")
        ):
            return cached

    except Exception as error:
        print(
            "[Market] Iran metals persistent cache read failed: "
            f"{error}"
        )

    return None


def get_cached_iran_local_metals_prices() -> dict | None:
    """Return the newest shared cache without making a network request.

    The persistent cache is checked FIRST because each application worker has
    its own in-memory cache. If memory were checked first, an API worker could
    keep serving an old response even after the background updater had written
    newer TGJU data to the shared cache file.
    """
    cached = _load_persistent_iran_metals_cache()
    if cached:
        _tgju_local_metals_cache["data"] = cached
        _tgju_local_metals_cache["fetched_at"] = time.time()
        return cached

    # If the cache file is temporarily unavailable, use the last successful
    # in-memory response rather than making the endpoint fail.
    return _tgju_local_metals_cache.get("data")


def _save_persistent_iran_metals_cache(data: dict) -> None:
    """Persist the last successful TGJU response atomically."""
    temp_file = TGJU_LOCAL_METALS_CACHE_FILE + ".tmp"

    try:
        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            TGJU_LOCAL_METALS_CACHE_FILE
        )

    except Exception as error:
        print(
            "[Market] Iran metals persistent cache write failed: "
            f"{error}"
        )

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except OSError:
            pass


def get_iran_local_metals_prices(
    force_refresh: bool = False
) -> dict:
    """
    Get Iranian local gold, silver and coin prices from TGJU.

    Normal API calls return the last successful cached response
    immediately. The background updater calls this function with
    ``force_refresh=True`` so only the updater talks to TGJU.
    """
    now = time.time()

    if not force_refresh:
        memory_cached = _tgju_local_metals_cache.get("data")

        if (
            memory_cached
            and now - _tgju_local_metals_cache["fetched_at"]
            < TGJU_LOCAL_METALS_CACHE_SECONDS
        ):
            return memory_cached

        persistent_cached = _load_persistent_iran_metals_cache()

        if persistent_cached:
            _tgju_local_metals_cache["data"] = persistent_cached
            _tgju_local_metals_cache["fetched_at"] = now
            return persistent_cached

    metals_html = _make_text_request(
        TGJU_LOCAL_MARKETS_URL
    )

    coin_html = _make_text_request(
        TGJU_COIN_URL
    )

    data = _tgju_parse_local_metals(
        metals_html
    )

    coins = _tgju_parse_coins(
        coin_html
    )

    data.extend(coins)

    if not data:
        raise RuntimeError(
            "TGJU Iran local gold/silver/coin prices "
            "could not be parsed."
        )

    result = {
        "category": "iran_precious_metals",
        "currency": "IRT",
        "unit_name": "Iranian Toman",
        "source": "TGJU",
        "source_url": TGJU_LOCAL_MARKETS_URL,
        "updated_at": datetime.utcnow().isoformat(),
        "count": len(data),
        "data": data,
    }

    _tgju_local_metals_cache["data"] = result
    _tgju_local_metals_cache["fetched_at"] = now

    _save_persistent_iran_metals_cache(result)

    print(
        "[Market] TGJU Iran local metals/coins updated: "
        + ", ".join(
            f"{item['symbol']}={item['price']}"
            for item in data
        )
    )

    return result

def _normalize_currency_code(value: str) -> str:
    value = (value or "").upper().strip()

    supported_codes = (
        "USD", "EUR", "GBP", "IRR", "PKR",
        "INR", "SAR", "AED", "CHF", "AUD",
        "CAD", "RUB", "DKK", "SEK", "NOK",
        "TRY", "CNY", "KWD", "QAR", "BHD", "JPY",
    )

    for code in supported_codes:
        if value.startswith(code):
            return code

    return ""


def _parse_afn_market_rates(html: str, market: str) -> dict:
    parser = _KhorasanTableParser()
    parser.feed(html)

    supported = {
        "USD", "EUR", "GBP", "IRR", "PKR",
        "INR", "SAR", "AED", "CHF", "AUD",
        "CAD", "RUB", "DKK", "SEK", "NOK",
        "TRY", "CNY", "KWD", "QAR", "BHD", "JPY",
    }

    required = {"USD", "EUR", "GBP", "IRR", "PKR"}

    # Sarai's dedicated page contains one complete Sarai table,
    # plus a short summary containing the same first five currencies.
    # For Sarai we collect every supported currency from that page.
    if market == "Sarai Shahzada":
        rates = {}

        for row in parser.rows:
            if len(row) < 3:
                continue

            code = _normalize_currency_code(row[0])
            if code not in supported:
                continue

            try:
                buy = float(str(row[1]).replace(",", "").strip())
                sell = float(str(row[2]).replace(",", "").strip())
            except (TypeError, ValueError):
                continue

            if buy <= 0 or sell <= 0:
                continue

            rates[code] = {
                "buy": buy,
                "sell": sell,
            }

        if not required.issubset(rates):
            raise RuntimeError(
                "Sarai Shahzada AFN rates could not be parsed."
            )

        return rates

    # Khorasan's page contains multiple Afghan-market tables.
    # Select the first complete five-currency sequence so the
    # Sarai/DAB tables later on the page cannot overwrite Khorasan.
    current = {}

    for row in parser.rows:
        if len(row) < 3:
            continue

        code = _normalize_currency_code(row[0])
        if code not in required:
            continue

        try:
            buy = float(str(row[1]).replace(",", "").strip())
            sell = float(str(row[2]).replace(",", "").strip())
        except (TypeError, ValueError):
            continue

        if buy <= 0 or sell <= 0:
            continue

        current[code] = {
            "buy": buy,
            "sell": sell,
        }

        if required.issubset(current):
            return current

    raise RuntimeError(
        f"{market} AFN rates could not be parsed."
    )


def get_khorasan_afn_prices() -> dict:

    """

    Get Afghan-market FX rates from Khorasan Market.



    Khorasan publishes buy and sell prices. Because the database

    currently stores one MarketPrice value per asset, we store the

    midpoint of buy and sell as the displayed market price.



    Units:

        USD/EUR/GBP = per 1 unit

        IRR          = per 1,000 Iranian Toman

        PKR          = per 1,000 Pakistani Rupees

    """



    html = _make_text_request(

        KHORASAN_RATES_URL

    )



    rates = _parse_afn_market_rates(

        html,
        "Khorasan Market"

    )



    result = {}



    mapping = {

        "USD": "USD_AFN",

        "EUR": "EUR_AFN",

        "GBP": "GBP_AFN",

        "IRR": "IRT_AFN",

        "PKR": "PKR_AFN",

    }



    for code, internal_symbol in mapping.items():



        item = rates.get(code)



        if not item:

            continue



        midpoint = (

            item["buy"] + item["sell"]

        ) / 2



        result[internal_symbol] = _fx_result(

            midpoint

        )



    if not result:

        raise RuntimeError(

            "Khorasan Market returned no supported AFN rates."

        )



    print(

        "[Market] Khorasan Market AFN rates updated: "

        + ", ".join(

            f"{symbol}={data['price']}"

            for symbol, data in result.items()

        )

    )



    return result





def get_sarai_shahzada_afn_prices() -> dict:
    """
    Get the complete Sarai Shahzada currency table from its
    dedicated sarafi.af page.
    """
    html = _make_text_request(
        SARAI_SHAHZADA_RATES_URL
    )

    rates = _parse_afn_market_rates(
        html,
        "Sarai Shahzada"
    )

    mapping = {
        "USD": "USD_AFN_SARAI",
        "EUR": "EUR_AFN_SARAI",
        "GBP": "GBP_AFN_SARAI",
        "IRR": "IRT_AFN_SARAI",
        "PKR": "PKR_AFN_SARAI",
        "SAR": "SAR_AFN_SARAI",
        "AED": "AED_AFN_SARAI",
        "CHF": "CHF_AFN_SARAI",
        "AUD": "AUD_AFN_SARAI",
        "CAD": "CAD_AFN_SARAI",
        "RUB": "RUB_AFN_SARAI",
        "DKK": "DKK_AFN_SARAI",
        "SEK": "SEK_AFN_SARAI",
        "NOK": "NOK_AFN_SARAI",
        "TRY": "TRY_AFN_SARAI",
        "CNY": "CNY_AFN_SARAI",
        "KWD": "KWD_AFN_SARAI",
        "QAR": "QAR_AFN_SARAI",
        "BHD": "BHD_AFN_SARAI",
        "JPY": "JPY_AFN_SARAI",
    }

    result = {}

    for code, internal_symbol in mapping.items():
        item = rates.get(code)
        if not item:
            continue

        result[internal_symbol] = _fx_result(
            (item["buy"] + item["sell"]) / 2
        )

    if not result:
        raise RuntimeError(
            "Sarai Shahzada returned no supported AFN rates."
        )

    print(
        "[Market] Sarai Shahzada AFN rates updated: "
        + ", ".join(
            f"{symbol}={data['price']}"
            for symbol, data in result.items()
        )
    )

    return result


def _parse_dab_inr_rate(html: str) -> dict:

    """

    Extract Indian Rupee / Afghan Afghani from the official

    Da Afghanistan Bank exchange-rate table.



    DAB columns are: Currency, Cash Sell, Cash Buy,

    Transfer Sell, Transfer Buy.



    We use the midpoint of Transfer Sell and Transfer Buy as

    the single displayed INR_AFN market price.

    """



    parser = _KhorasanTableParser()

    parser.feed(html)



    for row in parser.rows:



        if len(row) < 5:

            continue



        currency = (row[0] or "").strip().upper()



        if not (

            currency.startswith("INDIAN")

            or "INDIAN RS" in currency

        ):

            continue



        try:

            transfer_sell = float(

                row[3].replace(",", "")

            )

            transfer_buy = float(

                row[4].replace(",", "")

            )

        except (TypeError, ValueError):

            continue



        if transfer_sell <= 0 or transfer_buy <= 0:

            continue



        return {

            "buy": transfer_buy,

            "sell": transfer_sell,

            "price": (

                transfer_sell + transfer_buy

            ) / 2,

        }



    raise RuntimeError(

        "Da Afghanistan Bank INR/AFN rate could not be parsed."

    )





def get_dab_inr_afn_price() -> dict:
    """Get Indian Rupee / Afghan Afghani from Da Afghanistan Bank.

    The DAB page has changed host variants over time, so try the
    configured official URLs until one returns a parseable INR row.
    """
    last_error = None

    for url in DAB_RATES_URLS:
        try:
            html = _make_text_request(url)
            rate = _parse_dab_inr_rate(html)
            result = _fx_result(rate["price"])
            print(
                "[Market] Da Afghanistan Bank INR_AFN updated: "
                f"{result['price']}"
            )
            return result
        except Exception as error:
            last_error = error
            print(
                "[Market] DAB INR source failed: "
                f"{url} -> {error}"
            )

    raise RuntimeError(
        "Da Afghanistan Bank INR/AFN update failed: "
        f"{last_error}"
    )


def get_afghan_fx_prices() -> dict:

    """
    Afghan Afghani prices from Khorasan, Sarai Shahzada,
    and Da Afghanistan Bank.
    """

    result = {}

    try:
        result.update(
            get_khorasan_afn_prices()
        )
    except Exception as error:
        print(
            f"[Market] Khorasan Market update failed: {error}"
        )

    try:
        result.update(
            get_sarai_shahzada_afn_prices()
        )
    except Exception as error:
        print(
            f"[Market] Sarai Shahzada update failed: {error}"
        )

    try:
        result["INR_AFN"] = get_dab_inr_afn_price()
    except Exception as error:
        print(
            "[Market] Da Afghanistan Bank INR_AFN update failed: "
            f"{error}"
        )

    return result



def get_all_fx_prices() -> dict:

    """

    Fetch Iran FX from Servix and Afghanistan FX from Khorasan

    Market.

    """



    result = {}



    # Iran: Servix

    try:

        result.update(

            get_iran_fx_prices()

        )

    except Exception as error:

        print(

            f"[Market] Iran FX update failed: {error}"

        )



    # Afghanistan: Khorasan Market + official DAB INR

    try:

        result.update(

            get_afghan_fx_prices()

        )

    except Exception as error:

        print(

            f"[Market] Afghanistan FX update failed: {error}"

        )



    return result





# =========================================================

# All market prices

# =========================================================



def get_all_market_prices(

    symbols: list[str] | None = None

) -> dict:



    prices = {}



    # -----------------------------------------

    # Crypto

    # -----------------------------------------



    try:



        crypto_prices = get_crypto_prices(

            symbols

        )



        prices.update(

            crypto_prices

        )



    except Exception as error:



        print(

            f"[Market] "

            f"Crypto update failed: "

            f"{error}"

        )



    # -----------------------------------------

    # Gold

    # -----------------------------------------



    try:



        gold_price = get_gold_price()



        if gold_price:



            prices["GOLD"] = (

                gold_price

            )



    except Exception as error:



        print(

            f"[Market] "

            f"Gold update failed: "

            f"{error}"

        )



    # -----------------------------------------

    # Energy / Oil

    # -----------------------------------------



    try:



        energy_prices = (

            get_energy_prices()

        )



        if energy_prices:



            prices.update(

                energy_prices

            )



    except Exception as error:



        print(

            f"[Market] "

            f"Energy update failed: "

            f"{error}"

        )



    # -----------------------------------------

    # Iran / Afghanistan FX

    # -----------------------------------------



    try:



        fx_prices = (

            get_all_fx_prices()

        )



        if fx_prices:



            prices.update(

                fx_prices

            )



    except Exception as error:



        print(

            f"[Market] "

            f"FX update failed: "

            f"{error}"

        )



    return prices





# =========================================================

# Save prices

# =========================================================



def _ensure_market_asset(db: Session, symbol: str) -> Asset | None:
    """
    Create provider assets that were not present in older seed data.
    """
    symbol = symbol.upper().strip()

    asset = db.execute(
        select(Asset).where(Asset.symbol == symbol)
    ).scalar_one_or_none()

    if asset:
        return asset

    if symbol.endswith("_SARAI"):
        base = symbol[:-6]
        asset = Asset(
            symbol=symbol,
            name=f"{base} / Afghan Afghani - Sarai Shahzada",
            network="Sarai Shahzada",
            asset_type="forex",
            quote_currency="AFN",
            is_active=True,
        )
    elif symbol == "INR_AFN":
        asset = Asset(
            symbol=symbol,
            name="Indian Rupee / Afghan Afghani - Da Afghanistan Bank",
            network="Da Afghanistan Bank",
            asset_type="forex",
            quote_currency="AFN",
            is_active=True,
        )
    elif symbol in COIN_IDS:
        asset = Asset(
            symbol=symbol,
            name=f"{symbol} / Tether",
            network="CoinGecko",
            asset_type="crypto",
            quote_currency="USDT",
            is_active=True,
        )
    else:
        return None

    db.add(asset)
    db.flush()

    print(f"[Market] Asset auto-created: {symbol}")
    return asset


def save_market_prices(

    db: Session,

    prices: dict

) -> int:



    saved_count = 0



    for symbol, price_data in prices.items():



        asset = _ensure_market_asset(db, symbol)

        if not asset:
            print(
                f"[Market] Asset not found and cannot be auto-created: {symbol}"
            )
            continue



        price = price_data.get(

            "price"

        )



        if price is None:



            continue



        recorded_at = datetime.utcnow()



        # -------------------------------------------------

        # Oil 24h change

        # -------------------------------------------------

        # OilPriceAPI's latest endpoint does not provide a

        # reliable 24h percentage in our response. For oil,

        # calculate it from our own stored market history.

        #

        # We use the latest stored price that is at least

        # 24 hours old. If there is not enough history yet,

        # the value remains 0 until 24h of data exists.

        # -------------------------------------------------



        change_24h = (

            price_data.get(

                "change_24h",

                0

            )

            or 0

        )



        if symbol in {

            "BRENT",

            "WTI",

            "URALS"

        }:



            target_time = (

                recorded_at

                - timedelta(hours=24)

            )



            previous_result = db.execute(

                select(MarketPrice)

                .where(

                    MarketPrice.asset_id == asset.id,

                    MarketPrice.recorded_at <= target_time

                )

                .order_by(

                    MarketPrice.recorded_at.desc()

                )

                .limit(1)

            )



            previous_price = (

                previous_result.scalars().first()

            )



            if (

                previous_price is not None

                and previous_price.price is not None

                and float(previous_price.price) > 0

            ):



                change_24h = (

                    (

                        float(price)

                        - float(previous_price.price)

                    )

                    / float(previous_price.price)

                ) * 100



        market_price = MarketPrice(



            asset_id=asset.id,



            price=price,



            change_24h=change_24h,



            volume_24h=(

                price_data.get(

                    "volume_24h"

                )

            ),



            market_cap=(

                price_data.get(

                    "market_cap"

                )

            ),



            recorded_at=recorded_at

        )



        db.add(

            market_price

        )



        # -------------------------------------------------

        # One-minute candle

        # -------------------------------------------------

        # Crypto candles are generated from the live

        # price snapshots received from CoinGecko.


        # live price snapshots received from CoinGecko.

        #

        # CoinGecko's volume_24h is a rolling 24-hour value,

        # not 1-minute volume, so volume is intentionally

        # stored as NULL for these candles.

        #

        # This function is also used for Gold/Oil/FX snapshots.

        # -------------------------------------------------



        upsert_one_minute_candle(

            db=db,

            asset=asset,

            price=float(price),

            recorded_at=recorded_at,

            volume=None

        )

        if asset.asset_type == "crypto":
            for interval_minutes in (60, 240, 1440):
                upsert_external_ohlcv_candle(
                    db,
                    asset,
                    recorded_at=recorded_at,
                    open_price=float(price),
                    high_price=float(price),
                    low_price=float(price),
                    close_price=float(price),
                    volume=None,
                    interval_minutes=interval_minutes,
                )



        saved_count += 1



    if saved_count > 0:

        db.commit()



    return saved_count
