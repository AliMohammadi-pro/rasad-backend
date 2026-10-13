import threading
import time

from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import User
from app.services.portfolio_snapshot_service import (
    create_portfolio_snapshot
)


SNAPSHOT_INTERVAL = 300  # 5 minutes


def create_snapshots_for_all_users():
    db = SessionLocal()

    try:

        users = db.execute(
            select(User)
            .where(
                User.is_active == True
            )
        ).scalars().all()

        created_count = 0

        for user in users:

            try:

                create_portfolio_snapshot(
                    db,
                    user
                )

                created_count += 1

            except Exception as error:

                db.rollback()

                print(
                    f"[Portfolio] "
                    f"Snapshot failed for user "
                    f"{user.id}: {error}"
                )

        print(
            f"[Portfolio] Snapshots created: "
            f"{created_count}"
        )

    except Exception as error:

        db.rollback()

        print(
            f"[Portfolio] Snapshot updater error: "
            f"{error}"
        )

    finally:

        db.close()


def portfolio_snapshot_loop():

    print(
        "[Portfolio] "
        "Automatic snapshot updater started"
    )

    while True:

        try:

            create_snapshots_for_all_users()

        except Exception as error:

            print(
                f"[Portfolio] "
                f"Updater loop error: {error}"
            )

        time.sleep(
            SNAPSHOT_INTERVAL
        )


def start_portfolio_snapshot_updater():

    thread = threading.Thread(
        target=portfolio_snapshot_loop,
        daemon=True,
        name="portfolio-snapshot-updater"
    )

    thread.start()

    return thread