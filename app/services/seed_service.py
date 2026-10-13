from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset


# ==================================================
# Crypto Assets
# ==================================================

CRYPTO_ASSETS = [
('1INCH', '1inch', 'CoinGecko'),
('AAVE', 'Aave', 'Ethereum'),
('ADA', 'Cardano', 'Cardano'),
('AIOZ', 'AIOZ Network', 'CoinGecko'),
('ALGO', 'Algorand', 'Algorand'),
('APE', 'ApeCoin', 'CoinGecko'),
('APT', 'Aptos', 'Aptos'),
('AR', 'Arweave', 'CoinGecko'),
('ARB', 'Arbitrum', 'Arbitrum'),
('ASTR', 'Astar', 'CoinGecko'),
('ATOM', 'Cosmos', 'Cosmos'),
('AVAX', 'Avalanche', 'Avalanche'),
('AXS', 'Axie Infinity', 'CoinGecko'),
('BCH', 'Bitcoin Cash', 'Bitcoin Cash'),
('BLUR', 'Blur', 'CoinGecko'),
('BNB', 'BNB', 'BNB Chain'),
('BONK', 'Bonk', 'Solana'),
('BRETT', 'Brett', 'CoinGecko'),
('BTC', 'Bitcoin', 'Bitcoin'),
('CAKE', 'PancakeSwap', 'CoinGecko'),
('CELO', 'Celo', 'CoinGecko'),
('CHZ', 'Chiliz', 'CoinGecko'),
('COMP', 'Compound', 'CoinGecko'),
('CRO', 'Cronos', 'Cronos'),
('CRV', 'Curve DAO', 'CoinGecko'),
('DAI', 'Dai', 'CoinGecko'),
('DASH', 'Dash', 'CoinGecko'),
('DOGE', 'Dogecoin', 'Dogecoin'),
('DOT', 'Polkadot', 'Polkadot'),
('DYDX', 'dYdX', 'CoinGecko'),
('EGLD', 'MultiversX', 'MultiversX'),
('ENA', 'Ethena', 'CoinGecko'),
('ENJ', 'Enjin Coin', 'CoinGecko'),
('EOS', 'EOS', 'EOS'),
('ETC', 'Ethereum Classic', 'Ethereum Classic'),
('ETH', 'Ethereum', 'Ethereum'),
('FET', 'Artificial Superintelligence Alliance', 'Ethereum'),
('FIL', 'Filecoin', 'Filecoin'),
('FLOKI', 'FLOKI', 'CoinGecko'),
('FLOW', 'Flow', 'CoinGecko'),
('GALA', 'Gala', 'CoinGecko'),
('GMX', 'GMX', 'CoinGecko'),
('GRAM', 'Gram', 'TON'),
('GRT', 'The Graph', 'CoinGecko'),
('HBAR', 'Hedera', 'Hedera'),
('HYPE', 'Hyperliquid', 'CoinGecko'),
('ICP', 'Internet Computer', 'Internet Computer'),
('ILV', 'Illuvium', 'CoinGecko'),
('IMX', 'Immutable', 'Ethereum'),
('INJ', 'Injective', 'Injective'),
('IOTA', 'IOTA', 'CoinGecko'),
('IOTX', 'IoTeX', 'CoinGecko'),
('JASMY', 'JasmyCoin', 'CoinGecko'),
('JTO', 'Jito', 'CoinGecko'),
('JUP', 'Jupiter', 'Solana'),
('KAS', 'Kaspa', 'Kaspa'),
('KAVA', 'Kava', 'CoinGecko'),
('KSM', 'Kusama', 'CoinGecko'),
('LDO', 'Lido DAO', 'CoinGecko'),
('LINK', 'Chainlink', 'Ethereum'),
('LTC', 'Litecoin', 'Litecoin'),
('LUNC', 'Terra Luna Classic', 'CoinGecko'),
('MANA', 'Decentraland', 'CoinGecko'),
('MINA', 'Mina', 'CoinGecko'),
('MKR', 'Maker', 'Ethereum'),
('MNT', 'Mantle', 'CoinGecko'),
('NEAR', 'NEAR Protocol', 'NEAR'),
('NEO', 'NEO', 'CoinGecko'),
('NOT', 'Notcoin', 'CoinGecko'),
('OKB', 'OKB', 'CoinGecko'),
('ONDO', 'Ondo', 'CoinGecko'),
('ONE', 'Harmony', 'CoinGecko'),
('OP', 'Optimism', 'Optimism'),
('PENDLE', 'Pendle', 'CoinGecko'),
('PEPE', 'Pepe', 'Ethereum'),
('POL', 'Polygon', 'Polygon'),
('PYTH', 'Pyth Network', 'Solana'),
('QNT', 'Quant', 'CoinGecko'),
('RAY', 'Raydium', 'CoinGecko'),
('RENDER', 'Render', 'Solana'),
('ROSE', 'Oasis', 'CoinGecko'),
('RPL', 'Rocket Pool', 'CoinGecko'),
('RUNE', 'THORChain', 'CoinGecko'),
('SAND', 'The Sandbox', 'CoinGecko'),
('SEI', 'Sei', 'Sei'),
('SHIB', 'Shiba Inu', 'Ethereum'),
('SNX', 'Synthetix', 'CoinGecko'),
('SOL', 'Solana', 'Solana'),
('STRK', 'Starknet', 'CoinGecko'),
('STX', 'Stacks', 'Bitcoin'),
('SUI', 'Sui', 'Sui'),
('SUSHI', 'Sushi', 'CoinGecko'),
('TAO', 'Bittensor', 'CoinGecko'),
('THETA', 'Theta Network', 'Theta'),
('TIA', 'Celestia', 'Celestia'),
('TON', 'Toncoin', 'CoinGecko'),
('TRUMP', 'Official Trump', 'CoinGecko'),
('TRX', 'TRON', 'TRON'),
('TURBO', 'Turbo', 'CoinGecko'),
('UNI', 'Uniswap', 'Ethereum'),
('USDC', 'USD Coin', 'CoinGecko'),
('USDT', 'Tether', 'CoinGecko'),
('VET', 'VeChain', 'VeChain'),
('WIF', 'dogwifhat', 'Solana'),
('WLD', 'Worldcoin', 'CoinGecko'),
('XDC', 'XDC Network', 'CoinGecko'),
('XLM', 'Stellar', 'Stellar'),
('XMR', 'Monero', 'CoinGecko'),
('XRP', 'XRP', 'XRP Ledger'),
('XTZ', 'Tezos', 'Tezos'),
('ZEC', 'Zcash', 'CoinGecko'),
('ZK', 'ZKsync', 'CoinGecko'),
]


# ==================================================
# Energy / Oil Assets
# ==================================================

ENERGY_ASSETS = [
    ("BRENT", "Brent Crude Oil", "Commodity"),
    ("WTI", "WTI Crude Oil", "Commodity"),
    ("URALS", "Urals Crude Oil", "Commodity"),
]


# ==================================================
# Iran FX Assets
# ==================================================

IRAN_FX_ASSETS = [
    ("USD_IRT", "US Dollar / Iranian Toman"),
    ("EUR_IRT", "Euro / Iranian Toman"),
    ("GBP_IRT", "British Pound / Iranian Toman"),
    ("AED_IRT", "UAE Dirham / Iranian Toman"),
    ("TRY_IRT", "Turkish Lira / Iranian Toman"),
    ("CNY_IRT", "Chinese Yuan / Iranian Toman"),
    ("INR_IRT", "Indian Rupee / Iranian Toman"),
    ("CAD_IRT", "Canadian Dollar / Iranian Toman"),
    ("AUD_IRT", "Australian Dollar / Iranian Toman"),
    ("RUB_IRT", "Russian Ruble / Iranian Toman"),
    ("AFN_IRT", "Afghan Afghani / Iranian Toman"),
    ("IQD_IRT", "Iraqi Dinar / Iranian Toman"),
]


# ==================================================
# Iran Gold / Silver / Coins
# ==================================================

IRAN_METALS_ASSETS = [
    ("GOLD18_IRT", "Iran Gold 18K / Gram"),
    ("GOLD24_IRT", "Iran Gold 24K / Gram"),
    ("GOLD_USED_IRT", "Iran Used Gold / Gram"),
    ("MESGHAL_IRT", "Iran Gold Mesghal"),

    ("SILVER999_IRT", "Iran Silver 999 / Gram"),
    ("SILVER925_IRT", "Iran Silver 925 / Gram"),

    ("COIN_EMAMI_IRT", "Iran Emami Coin"),
    ("COIN_BAHAR_IRT", "Iran Bahar Azadi Coin"),
    ("COIN_HALF_IRT", "Iran Half Coin"),
    ("COIN_QUARTER_IRT", "Iran Quarter Coin"),
    ("COIN_GRAMI_IRT", "Iran Gram Coin"),
]


# ==================================================
# Afghanistan FX Assets
# ==================================================

AFGHAN_FX_ASSETS = [
    # Khorasan Market
    ("USD_AFN", "US Dollar / Afghan Afghani"),
    ("EUR_AFN", "Euro / Afghan Afghani"),
    ("GBP_AFN", "British Pound / Afghan Afghani"),
    ("IRT_AFN", "Iranian Toman / Afghan Afghani"),
    ("PKR_AFN", "Pakistani Rupee / Afghan Afghani"),

    # Da Afghanistan Bank
    ("INR_AFN", "Indian Rupee / Afghan Afghani"),
]


# ==================================================
# Afghanistan FX - Sarai Shahzada
# ==================================================

SARAI_SHAHZADA_FX_ASSETS = [
('USD_AFN_SARAI', 'US Dollar / Afghan Afghani - Sarai Shahzada'),
('EUR_AFN_SARAI', 'Euro / Afghan Afghani - Sarai Shahzada'),
('GBP_AFN_SARAI', 'British Pound / Afghan Afghani - Sarai Shahzada'),
('IRT_AFN_SARAI', 'Iranian Toman / Afghan Afghani - Sarai Shahzada'),
('PKR_AFN_SARAI', 'Pakistani Rupee / Afghan Afghani - Sarai Shahzada'),
('SAR_AFN_SARAI', 'Saudi Riyal / Afghan Afghani - Sarai Shahzada'),
('AED_AFN_SARAI', 'UAE Dirham / Afghan Afghani - Sarai Shahzada'),
('CHF_AFN_SARAI', 'Swiss Franc / Afghan Afghani - Sarai Shahzada'),
('AUD_AFN_SARAI', 'Australian Dollar / Afghan Afghani - Sarai Shahzada'),
('CAD_AFN_SARAI', 'Canadian Dollar / Afghan Afghani - Sarai Shahzada'),
('RUB_AFN_SARAI', 'Russian Ruble / Afghan Afghani - Sarai Shahzada'),
('DKK_AFN_SARAI', 'Danish Krone / Afghan Afghani - Sarai Shahzada'),
('SEK_AFN_SARAI', 'Swedish Krona / Afghan Afghani - Sarai Shahzada'),
('NOK_AFN_SARAI', 'Norwegian Krone / Afghan Afghani - Sarai Shahzada'),
('TRY_AFN_SARAI', 'Turkish Lira / Afghan Afghani - Sarai Shahzada'),
('CNY_AFN_SARAI', 'Chinese Yuan / Afghan Afghani - Sarai Shahzada'),
('KWD_AFN_SARAI', 'Kuwaiti Dinar / Afghan Afghani - Sarai Shahzada'),
('QAR_AFN_SARAI', 'Qatari Riyal / Afghan Afghani - Sarai Shahzada'),
('BHD_AFN_SARAI', 'Bahraini Dinar / Afghan Afghani - Sarai Shahzada'),
('JPY_AFN_SARAI', 'Japanese Yen / Afghan Afghani - Sarai Shahzada'),
]


# ==================================================
# Afghanistan Gold - Herat
# ==================================================

AFGHAN_GOLD_ASSETS = [
    ("HERAT_GOLD_18K", "Herat Gold 18K / Gram"),
    ("HERAT_GOLD_21K", "Herat Gold 21K / Gram"),

    ("HERAT_COIN_QUARTER", "Herat Quarter Coin"),
    ("HERAT_COIN_HALF", "Herat Half Coin"),
    ("HERAT_COIN_FULL", "Herat Full Coin"),

    # اگر بعداً خواستیم طلای آب‌شده را هم در Asset ذخیره کنیم:
    # ("HERAT_GOLD_MELTED", "Herat Melted Gold / Gram"),
]


# ==================================================
# Unsupported old Afghan FX assets
# ==================================================
#
# این موارد دیگر توسط منابع فعلی پروژه استفاده نمی‌شوند.
#
# INR_AFN را عمداً اینجا قرار نمی‌دهیم، چون منبع آن
# Da Afghanistan Bank است.
# ==================================================

UNSUPPORTED_KHORASAN_AFN_ASSETS = {
    "AED_AFN",
    "CNY_AFN",
    "TRY_AFN",
    "RUB_AFN",
}


# ==================================================
# Helper
# ==================================================

def _seed_asset(
    db: Session,
    symbol: str,
    name: str,
    network: str,
    asset_type: str,
    quote_currency: str,
) -> None:

    existing_asset = db.execute(
        select(Asset).where(
            Asset.symbol == symbol
        )
    ).scalar_one_or_none()

    # اگر Asset قبلاً وجود داشته باشد
    if existing_asset:

        # اطلاعات Asset را با تنظیمات فعلی هماهنگ می‌کنیم
        existing_asset.name = name
        existing_asset.network = network
        existing_asset.asset_type = asset_type
        existing_asset.quote_currency = quote_currency

        # مطمئن می‌شویم فعال باشد
        existing_asset.is_active = True

        return

    # اگر Asset وجود نداشته باشد، ایجاد می‌شود
    db.add(
        Asset(
            symbol=symbol,
            name=name,
            network=network,
            asset_type=asset_type,
            quote_currency=quote_currency,
            is_active=True,
        )
    )


# ==================================================
# Seed Assets
# ==================================================

def seed_assets(db: Session) -> None:

    # ==================================================
    # Crypto
    # ==================================================

    for symbol, name, network in CRYPTO_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            network,
            "crypto",
            "USDT",
        )


    # ==================================================
    # Global Gold
    # XAU/USD
    # ==================================================

    _seed_asset(
        db,
        "GOLD",
        "Gold",
        "Commodity",
        "commodity",
        "USD",
    )


    # ==================================================
    # Iran Gold / Silver / Coins
    # TGJU
    # ==================================================

    for symbol, name in IRAN_METALS_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            "TGJU",
            "gold",
            "IRT",
        )


    # ==================================================
    # Afghanistan Gold - Herat
    # ==================================================

    for symbol, name in AFGHAN_GOLD_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            "Herat Goldsmiths Union",
            "gold",
            "AFN",
        )


    # ==================================================
    # Energy / Oil
    # ==================================================

    for symbol, name, network in ENERGY_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            network,
            "energy",
            "USD",
        )


    # ==================================================
    # Iran FX
    # ==================================================

    for symbol, name in IRAN_FX_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            "Iran",
            "forex",
            "IRT",
        )


    # ==================================================
    # Afghanistan FX - Khorasan Market
    # ==================================================

    for symbol, name in AFGHAN_FX_ASSETS:

        # INR_AFN از Da Afghanistan Bank می‌آید
        if symbol == "INR_AFN":

            _seed_asset(
                db,
                symbol,
                name,
                "Da Afghanistan Bank",
                "forex",
                "AFN",
            )

        # سایر ارزهای افغانستان از Khorasan Market
        else:

            _seed_asset(
                db,
                symbol,
                name,
                "Khorasan Market",
                "forex",
                "AFN",
            )


    # ==================================================
    # Afghanistan FX - Sarai Shahzada
    # ==================================================

    for symbol, name in SARAI_SHAHZADA_FX_ASSETS:

        _seed_asset(
            db,
            symbol,
            name,
            "Sarai Shahzada",
            "forex",
            "AFN",
        )


    # ==================================================
    # Deactivate unsupported old Afghan FX
    # ==================================================

    for symbol in UNSUPPORTED_KHORASAN_AFN_ASSETS:

        existing_asset = db.execute(
            select(Asset).where(
                Asset.symbol == symbol
            )
        ).scalar_one_or_none()

        if existing_asset:

            existing_asset.is_active = False


    # ==================================================
    # Commit
    # ==================================================

    db.commit()