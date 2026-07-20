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

    ora_user = cfg.DB_USER_COLIN_ORACLE
    ora_password = cfg.DB_PASSWORD_COLIN_ORACLE
    ora_host = cfg.DB_HOST_COLIN_ORACLE
    ora_port = int(cfg.DB_PORT_COLIN_ORACLE)
    ora_name = cfg.DB_NAME_COLIN_ORACLE
    
    lines = [
        'register driver PostgreSql org.postgresql.Driver jdbc:postgresql://<host>:<port>/<db>?reWriteBatchedInserts=true "port=5432"',
        'register driver Oracle oracle.jdbc.OracleDriver jdbc:oracle:thin:@<host>:<port>:<db> "port=1521"',
        f'connection my_proxy_test -d PostgreSql -u {user} -p {password} -h {host} -P {port} -D {name}',
        f'connection cprd -d Oracle -u {ora_user} -p {ora_password} -h {ora_host} -P {ora_port} -D {ora_name}',

    ]

    init_path.write_text('\n'.join(lines) + '\n')

    return init_path
