import sys

from sqlalchemy import create_engine, text
from config import get_named_config

def run_check() -> int:
    cfg = get_named_config()
    if not all([cfg.DB_USER_COLIN_MIGR, cfg.DB_PASSWORD_COLIN_MIGR, cfg.DB_NAME_COLIN_MIGR, cfg.DB_HOST_COLIN_MIGR, cfg.DB_PORT_COLIN_MIGR]):
        raise RuntimeError(
            "Missing business env vars"
        )
    print(f"[business-api] connecting to {cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR}")
    engine = create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM corporation LIMIT 1")).mappings().first()
        if row is None:
            print("no rows in business mig db")
        else:
            print(f"sample row: {dict(row)}")
        return 0
    

if __name__ == "__main__":
    try:
        raise SystemExit(run_check())
    except Exception as exc:
        print(f"business db check failed: {exc}", file=sys.stderr)
        raise
