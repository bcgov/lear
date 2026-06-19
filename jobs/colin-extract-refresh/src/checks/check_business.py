import sys

from sqlalchemy import create_engine, text
from config import get_colin_mig_engine, get_named_config
from dbschemacli_init import write_dbschema_init
def run_check() -> int:
    cfg = get_named_config()
    if cfg.CLOUDSQL_INSTANCE_CONNECTION_NAME:
        if not all([cfg.CLOUDSQL_INSTANCE_CONNECTION_NAME, cfg.DB_NAME_COLIN_MIGR, cfg.DB_USER_COLIN_MIGR]):
            raise RuntimeError(
                "Missing business env vars"
            )
    print("== running check_business.py ==")
    if cfg.CLOUDSQL_INSTANCE_CONNECTION_NAME:
        print(f"connecting via cloud sql connector")
    engine = get_colin_mig_engine(cfg)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM businesses LIMIT 1")).mappings().first()
        if row is None:
            print("no rows in business mig db")
        else:
            print(f"row found........")
        return 0
    print(f"starting dbschema connection")
    write_dbschema_init()

if __name__ == "__main__":
    try:
        raise SystemExit(run_check())
    except Exception as exc:
        print(f"business db check failed......")
        raise
