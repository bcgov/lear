from pathlib import Path
from config import _Config

def write_dbschema_init(cfg: _Config) -> Path:
    init_dir = Path.home() / '.DbSchema' / 'cli'
    init_dir.mkdir(parents=True, exist_ok=True)
    init_path = init_dir / 'init.sql'
    db_user = cfg.DB_USER_COLIN_MIGR

    lines = [
        'register driver PostgreSql org.postgresql.Driver jdbc:postgresql://<host>:<port>/<db> "port=5432"'
    ]
