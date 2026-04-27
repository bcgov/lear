import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.states import Failed
from flask import current_app
from config import get_named_config
from common.colin_queries import get_updated_identifiers
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / 'data-tool' / 'scripts' / 'generate_cprd_subset_extract.py'
_GENERATED_DIR = _REPO_ROOT / 'data-tool' / 'scripts' / 'generated'
_DEFAULT_DDL = _REPO_ROOT / 'data-tool' / 'scripts' / 'colin_corps_extract_postgres_ddl'
_SUBSET = _GENERATED_DIR / 'subset_refresh.sql'

def _resolve_master_script_path(out: str | None) -> Path:
    if out:
        return Path(out).expanduser().resolve()
    return _SUBSET.resolve()

def _run_cmd(argv: list[str], env: dict[str, str] | None = None) -> None:
    r = subprocess.run(argv, cwd=str(_REPO_ROOT), capture_output=False, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f'command failed ({r.returncode}): {" ".join(argv)}')
    
def require_file(path: str | Path, description: str) -> Path:
    """File Not Found Error"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f'{description} not found (expected a file): {resolved}')
    return resolved


def _reset_extract_postgres_db() -> None:
    cfg = get_named_config()
    dbname = cfg.DB_NAME_COLIN_MIGR
    host = cfg.DB_HOST_COLIN_MIGR
    port = str(cfg.DB_PORT_COLIN_MIGR)
    user = cfg.DB_USER_COLIN_MIGR
    password = cfg.DB_PASSWORD_COLIN_MIGR
    
    require_file(_DEFAULT_DDL, 'Extract DDL File')

    pg_flags = ['-h', host, '-p', str(port), '-U', user]
    run_env = dict(os.environ)
    if password and 'PGPASSWORD' not in run_env:
        run_env['PGPASSWORD'] = password
    safe_db = str(dbname).replace("'", "''")
    terminate_sql = (
        "SELECT pg_terminate_backend(pg_stat_activity.pid) "
        "FROM pg_stat_activity "
        f"WHERE datname = '{safe_db}' AND pid <> pg_backend_pid();"
    )
    _run_cmd(['psql', *pg_flags, '-d', 'postgres', '-c', terminate_sql ], env=run_env)
    _run_cmd(['dropdb', *pg_flags, '--maintenance-db=postgres', '--if-exists', dbname ], env=run_env)
    _run_cmd(['createdb', *pg_flags, '--maintenance-db=postgres', '-T', 'template0', dbname ], env=run_env)
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', '-f', str(_DEFAULT_DDL) ], env=run_env)

@task(name='Cleanup-Extract-Postgres', cache_policy=NO_CACHE)
def cleanup_extract_postgres_db() -> None:
    _reset_extract_postgres_db()

@task(name='Get-Updated-Identifiers-Colin')
def get_updated_identifiers_colin() -> None:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    timestamp = '1234'
    corp_list = ['12345','5678']
    updated_corp_nums = [get_updated_identifiers(timestamp, corp_list )]
    print(updated_corp_nums.size())
    return updated_corp_nums

    
@task(name='Run-CPRD-Subset-Generator', cache_policy=NO_CACHE)
def run_cprd_subset_extract_generator(
    corp_file: str,
    mode: str,
    chunk_size: int,
    threads: int,
    pg_fastload: bool,
    pg_disable_method: str,
    out: str | None,
    include_cp: bool = False,
) -> subprocess.CompletedProcess:
    """
    Generate Commands
    """
    require_file(_SCRIPT_PATH, 'Generated script')
    corp_path =require_file(corp_file, 'Corp list file')
    
    argv = [
        sys.executable,
        str(_SCRIPT_PATH),
        '--corp-file',
        str(corp_path),
        '--mode',
        mode,
        '--chunk-size',
        str(chunk_size),
        '--threads',
        str(threads),
        '--pg-disable-method',
        pg_disable_method,
    ]
    if pg_fastload:
        argv.append('--pg-fastload')
    if include_cp:
        argv.append('--include-cp')
    out_path = Path(out).expanduser().resolve() if out is not None else _SUBSET.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argv.extend(['--out', str(out)])
    
    return subprocess.run(
        argv,
        cwd=str(_REPO_ROOT),
        capture_output=False,
        text=True,
    )

@task(name='DBSchemaCLI', cache_policy=NO_CACHE)
def run_dbschemacli_task(master_script: str, dbschemacli_cmd: str = 'dbschemacli') -> subprocess.CompletedProcess:
    master_script_path = Path(master_script)
    if not master_script_path.exists():
        raise FileNotFoundError(f'Generated script not found: {master_script_path}')
    print(f'Running: {dbschemacli_cmd} {master_script_path}')
    return subprocess.run(
        [dbschemacli_cmd, str(master_script_path)],
        cwd=str(_REPO_ROOT),
        capture_output=False,
        text=True,
    )

@flow(name='Extract-Subset-Flow', log_prints=True, persist_result=False)
def extract_pull_flow(
    corp_file: str,
    mode: str = 'load',
    chunk_size: int = 900,
    threads: int = 4,
    pg_fastload: bool = False,
    pg_disable_method: str = 'replica_role',
    out: str | None=None,
    run_dbschemacli: bool = False,
    dbschemacli_cmd: str = 'dbschemacli',
    reset_extract_postgres: bool = True,
    include_cp: bool = False,
) -> None:
    """
    Generate files
    """
    if reset_extract_postgres:
        cleanup_extract_postgres_db()

    print(f'Running CPRD subset extract generator {corp_file}')
    result = run_cprd_subset_extract_generator(
        corp_file=corp_file,
        mode=mode,
        chunk_size=chunk_size,
        threads=threads,
        pg_fastload=pg_fastload,
        include_cp=include_cp,
        pg_disable_method=pg_disable_method,
        out=out,
    )
    if result.returncode != 0:
        raise RuntimeError(f'Generator exited with code {result.returncode}')
    print(f'generator completed successfully')

    if run_dbschemacli:
        master_script = _resolve_master_script_path(out=out)
        run_result = run_dbschemacli_task(
            master_script=str(master_script),
            dbschemacli_cmd=dbschemacli_cmd,
        )
        if run_result.returncode != 0:
            raise RuntimeError(f'DbSchemaCLI exited with code {run_result.returncode}')

    

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Run Extract-Pull flow....')
    p.add_argument('corp_file', help='Path to newline-delimited corp identifiers')
    p.add_argument('--mode', default='load', choices=('refresh', 'load'))
    p.add_argument('--chunk-size', type=int, default=900, help='Max items per IN list.')
    p.add_argument('--threads', type=int, default=4, help='DBSchemaCLI transfer threads')
    p.add_argument('--pg-fastload', action='store_true', help='Enable Postgres fast-load')
    p.add_argument('--include-cp', action='store_true', help='Include corp type CP in subset extract queries')
    p.add_argument('--pg-disable-method', default='replica_role', choices=('table_triggers', 'replica_role'))
    p.add_argument('--out', default=None, help='Output path for generated master script.')
    p.add_argument('--run-dbschemacli', action='store_true')
    p.add_argument('--dbschemacli-cmd', default='dbschemacli')
    p.add_argument('--reset-extract-postgres', action='store_false')
    extract_pull_flow(**vars(p.parse_args()))
