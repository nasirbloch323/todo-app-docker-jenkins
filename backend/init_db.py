"""Wait for the database, then create tables and seed data. Runs once before gunicorn starts."""
import sys
import time

from sqlalchemy import text

from app import database_url, init_db, make_engine


def main():
    engine = make_engine(database_url())
    for attempt in range(1, 31):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as exc:  # noqa: BLE001
            print(f"Database not ready ({attempt}/30): {exc.__class__.__name__}", flush=True)
            time.sleep(2)
    else:
        sys.exit("Database never became ready")
    init_db(engine)
    print("Database initialised", flush=True)


if __name__ == "__main__":
    main()
