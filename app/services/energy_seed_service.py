from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset


ENERGY_ASSETS = [
    {
        "symbol": "BRENT",
        "name": "Brent Crude Oil",
        "network": "Commodity",
        "asset_type": "energy",
        "quote_currency": "USD",
    },
    {
        "symbol": "WTI",
        "name": "WTI Crude Oil",
        "network": "Commodity",
        "asset_type": "energy",
        "quote_currency": "USD",
    },
    {
        "symbol": "URALS",
        "name": "Urals Crude Oil",
        "network": "Commodity",
        "asset_type": "energy",
        "quote_currency": "USD",
    },
]


def seed_energy_assets(db: Session):

    created = 0

    for item in ENERGY_ASSETS:

        existing = db.execute(
            select(Asset)
            .where(
                Asset.symbol == item["symbol"]
            )
        ).scalar_one_or_none()

        if existing:
            continue

        asset = Asset(
            symbol=item["symbol"],
            name=item["name"],
            network=item["network"],
            asset_type=item["asset_type"],
            quote_currency=item["quote_currency"],
            is_active=True
        )

        db.add(asset)

        created += 1

    if created > 0:
        db.commit()

    return created