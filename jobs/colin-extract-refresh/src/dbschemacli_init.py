from pathlib import Path
import subprocess
from config import _Config

def write_dbschema_init(cfg: _Config) -> Path:
    init_dir = Path.home() / '.DbSchema' / 'cli'
    init_dir.mkdir(parents=True, exist_ok=True)
    init_path = init_dir / 'init.sql'
    user = cfg.DB_USER_COLIN_MIGR
    password = cfg.DB_PASSWORD_COLIN_MIGR
    host = cfg.DB_HOST_COLIN_MIGR
    port = int(cfg.DB_PORT_COLIN_MIGR)
    name = cfg.DB_NAME_COLIN_MIGR
    
    lines = [
        'register driver PostgreSql org.postgresql.Driver jdbc:postgresql://{HOST}:{PORT}/{DB} "port=5432"',
        f'connection my_proxy_test PostgreSql "user={user} password={password} host={host} port={port} db={name}"',
    ]

    init_path.write_text('\n'.join(lines) + '\n')

    return init_path
