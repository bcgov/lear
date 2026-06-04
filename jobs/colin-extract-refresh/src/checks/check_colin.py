import os
import sys
import oracledb
from sqlalchemy import create_engine, text
from config import get_named_config

def _colin_oracle_init() -> None:
    lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR", "")
    oracledb.init_oracle_client(lib_dir=lib_dir)
    print('👷 Enable thick mode:', not oracledb.is_thin_mode())
    print('👷 Instant Client version:', oracledb.clientversion())
        
    
def run_check() -> int:
    cfg = get_named_config()
    if not all([cfg.DB_USER_COLIN_ORACLE, cfg.DB_PASSWORD_COLIN_ORACLE, cfg.DB_NAME_COLIN_ORACLE, cfg.DB_HOST_COLIN_ORACLE, cfg.DB_PORT_COLIN_ORACLE]):
        raise RuntimeError(
            "Missing colin env vars"
        )
    print("== running check_colin.py ==")
    _colin_oracle_init()
    engine = create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_ORACLE)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM corporation FETCH FIRST 1 ROWS ONLY")).mappings().first()
        if row is None:
            print("no rows in COLIN  db")
        else:
            print(f"COLIN sample row: {dict(row)}")
        return 0
    

if __name__ == "__main__":
    try:
        raise SystemExit(run_check())
    except Exception as exc:
        print(f"business db check failed: {exc}", file=sys.stderr)
        raise
