import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import re
import subprocess
import sys
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.states import Failed
from flask import current_app
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime, timezone
from config import get_named_config
from common.colin_queries import get_identifiers_per_batch, get_updated_identifiers_for_batch, unfreeze_identifiers
from common.init_utils import colin_oracle_init, get_config
from common.query_utils import corpnum_to_oracle_ids, get_cutoff_timestamp_query, get_fallout_corp_nums, prune_candidates_from_account, prune_candidates_from_batch, prune_candidates_from_cp

_DEFAULT_TARGET_CONNECTION = get_named_config().TARGET_CONNECTION
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / 'data-tool' / 'scripts' / 'generate_cprd_subset_extract.py'
_GENERATED_DIR = _REPO_ROOT / 'data-tool' / 'scripts' / 'generated'
_DEFAULT_DDL = _REPO_ROOT / 'data-tool' / 'scripts' / 'colin_corps_extract_postgres_ddl'
_SUBSET = _GENERATED_DIR / 'subset_refresh.sql'
_REFRESH_VIEWS_SCRIPT = _REPO_ROOT / 'data-tool' / 'refresh_colin_extract_views.sh'
_BUILD_VIEWS_SCRIPT = _REPO_ROOT / 'data-tool' / 'scripts' / 'colin_corps_extract_postgres_views_ddl'


# =========================
# cfg_* (types & config)
# =========================

class cfg_GenerationMode(str, Enum):
    REFRESH = "refresh"  # delete + reload
    LOAD = "load"        # load only


class cfg_RenderMode(str, Enum):
    INLINE = "inline"    # render templates into chunk files (no vset)
    VSET = "vset"        # legacy behavior (runtime vset substitution)


class cfg_OracleInStrategy(str, Enum):
    AUTO = "auto"
    CHUNK_FILES = "chunk_files"
    OR_OF_IN_LISTS = "or_of_in_lists"


class cfg_PgDisableMethod(str, Enum):
    TABLE_TRIGGERS = "table_triggers"  # ALTER TABLE ... DISABLE/ENABLE TRIGGER ALL (default)
    REPLICA_ROLE = "replica_role"      # SET session_replication_role=replica|origin (superuser only)


class cfg_DeltaScope(str, Enum):
    BATCH = "batch"  # only process identifiers in the current batch
    FULL = "full"    # process all identifiers in the corp list

@dataclass
class SubsetConfig:
    corp_file: Path
    mode: cfg_GenerationMode
    chunk_size: int
    threads: int
    prefix_numeric_bc: bool
    include_cp: bool

    pg_fastload: bool
    pg_disable_method: cfg_PgDisableMethod

    out_master: Path
    run_dbschemacli: bool
    dbschemacli_cmd: str

    refresh_views: bool

    source_connection: str
    target_connection: str
    target_schema: str

    reset_extract_postgres: bool = True
    delta_scope: cfg_DeltaScope = cfg_DeltaScope.BATCH

    
def build_configs(args: argparse.Namespace) -> SubsetConfig:
    """Build SubsetConfig from parsed arguments."""
    return SubsetConfig(
        corp_file=Path(args.corp_file).expanduser().resolve(),
        mode=cfg_GenerationMode(args.mode),
        delta_scope=cfg_DeltaScope(args.delta_scope),
        chunk_size=args.chunk_size,
        threads=args.threads,
        prefix_numeric_bc=(args.mode == 'refresh'),
        include_cp=args.include_cp,
        pg_fastload=args.pg_fastload,
        pg_disable_method=cfg_PgDisableMethod(args.pg_disable_method),
        out_master=_resolve_master_script_path(args.out),
        run_dbschemacli=args.run_dbschemacli,
        dbschemacli_cmd=args.dbschemacli_cmd,
        refresh_views=args.refresh_views,
        reset_extract_postgres=args.reset_extract_postgres,
        source_connection=args.source_connection,
        target_connection=args.target_connection,
        target_schema=args.target_schema
    )


def _resolve_master_script_path(out: str | None) -> Path:
    if not out:
        return _SUBSET.resolve()
    p = Path(out).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (_REPO_ROOT / p).resolve()

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


def _normalize_target_schema(target_schema: str | None, default_schema: str = 'public') -> str:
    normalized = (target_schema or default_schema).strip()
    return normalized or default_schema


def _reset_extract_postgres_db(target_schema: str | None = 'public') -> None:
    cfg = get_named_config()
    dbname = cfg.DB_NAME_COLIN_MIGR
    host = cfg.DB_HOST_COLIN_MIGR
    port = str(cfg.DB_PORT_COLIN_MIGR)
    user = cfg.DB_USER_COLIN_MIGR
    password = cfg.DB_PASSWORD_COLIN_MIGR

    target_schema = _normalize_target_schema(target_schema)
    safe_schema = '"' + target_schema.replace('"', '""') + '"'
    search_path_sql = f'SET search_path TO {safe_schema};'
    create_schema_sql = f'CREATE SCHEMA IF NOT EXISTS {safe_schema};'
    psql_schema_vars = ['-v', f'schema_name={target_schema}']

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
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', *psql_schema_vars, '-c', create_schema_sql], env=run_env)
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', *psql_schema_vars, '-c', search_path_sql, '-f', str(_DEFAULT_DDL)], env=run_env)
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', *psql_schema_vars, '-c', search_path_sql, '-f', str(_BUILD_VIEWS_SCRIPT)], env=run_env)



# def _reset_extract_postgres_db() -> None:
#     cfg = get_named_config()
#     dbname = cfg.DB_NAME_COLIN_MIGR
#     host = cfg.DB_HOST_COLIN_MIGR
#     port = str(cfg.DB_PORT_COLIN_MIGR)
#     user = cfg.DB_USER_COLIN_MIGR
#     password = cfg.DB_PASSWORD_COLIN_MIGR
    
#     require_file(_DEFAULT_DDL, 'Extract DDL File')

#     pg_flags = ['-h', host, '-p', str(port), '-U', user]
#     run_env = dict(os.environ)
#     if password and 'PGPASSWORD' not in run_env:
#         run_env['PGPASSWORD'] = password
#     safe_db = str(dbname).replace("'", "''")
#     terminate_sql = (
#         "SELECT pg_terminate_backend(pg_stat_activity.pid) "
#         "FROM pg_stat_activity "
#         f"WHERE datname = '{safe_db}' AND pid <> pg_backend_pid();"
#     )
#     _run_cmd(['psql', *pg_flags, '-d', 'postgres', '-c', terminate_sql ], env=run_env)
#     _run_cmd(['dropdb', *pg_flags, '--maintenance-db=postgres', '--if-exists', dbname ], env=run_env)
#     _run_cmd(['createdb', *pg_flags, '--maintenance-db=postgres', '-T', 'template0', dbname ], env=run_env)
#     _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', '-f', str(_DEFAULT_DDL) ], env=run_env)
#     _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', '-f', str(_BUILD_VIEWS_SCRIPT) ], env=run_env)

@task(name='Get-Fallen-Out-Identifiers', cache_policy=NO_CACHE)
def get_fallen_identifiers(updated_corp_nums: list) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    if not updated_corp_nums:
        return []
    cfg = get_named_config()
    corp_nums_prune_list_query = get_fallout_corp_nums('SAF', updated_corp_nums)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).connect() as conn:
        result = conn.execute(text(corp_nums_prune_list_query)).scalars().all()
        rows = [str(row).strip() for row in result]
    return rows

@task(name='Prune-Fallen-Out-Identifiers', cache_policy=NO_CACHE)
def prune_fallen_identifiers(fallenout_corp_nums: list) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    if not fallenout_corp_nums:
        print(f"No fallout corps to prune")
        return
    cfg = get_named_config()
    fallen_out_identifiers_list = get_fallen_identifiers(fallenout_corp_nums)
    cp_query = prune_candidates_from_cp(fallen_out_identifiers_list)
    batch_query = prune_candidates_from_batch(fallen_out_identifiers_list)
    account_query = prune_candidates_from_account(fallen_out_identifiers_list)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        prune_cp = conn.execute(text(cp_query))
        prune_batch = conn.execute(text(batch_query))
        prune_account = conn.execute(text(account_query))
    print(f"Pruned corp_processing={prune_cp.rowcount}, mig_corp_batch={prune_batch.rowcount}, mig_corp_account={prune_account.rowcount}")

def get_cuttoff_timestamp(target_schema: str | None = 'public') -> datetime:

    cfg = get_named_config()
    cuttoff_timestamp = get_cutoff_timestamp_query(target_schema)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        cuttoff_timestamp_result = conn.execute(text(cuttoff_timestamp)).scalar()
    print(f"cuttoff timestamp is {cuttoff_timestamp_result}")
    return cuttoff_timestamp_result
    
# @task(name='Cleanup-Extract-Postgres', cache_policy=NO_CACHE)
# def cleanup_extract_postgres_db() -> None:
#     _reset_extract_postgres_db()

@task(name='Cleanup-Extract-Postgres', cache_policy=NO_CACHE)
def cleanup_extract_postgres_db(target_schema: str | None = 'public') -> None:
    _reset_extract_postgres_db(target_schema=target_schema)

@task(name='Unfreeze-Identifiers', cache_policy=NO_CACHE)
def run_unfreeze_identifiers(target_schema: str | None = 'public') -> None:
    cfg = get_named_config()
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        result = conn.execute(text(unfreeze_identifiers(target_schema=target_schema)))
    print(f'Unfroze corporation rows={result.rowcount}')

@task(name='Get-Updated-Identifiers-Colin', cache_policy=NO_CACHE)
def get_updated_identifiers_colin(cutoff_timestamp: str, mig_batch_id: int, colin_oracle_engine: Engine, chunk_size: int, scope: str) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    cfg = get_named_config()
    corp_list = ''
    if scope == 'batch':
        mig_sql = get_identifiers_per_batch(mig_batch_id)
        with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).connect() as conn:
            row = conn.execute(text(mig_sql)).fetchone()
    
        corp_list = corpnum_to_oracle_ids(row[0]) if row else None    
    colin_sql = get_updated_identifiers_for_batch(cutoff_timestamp, str(corp_list or ''), chunk_size, scope)

    with colin_oracle_engine.connect() as conn:
        result = conn.execute(text(colin_sql))
        rows = [dict(row) for row in result.mappings()]
    return rows


@task(name='Run-CPRD-Subset-Generator', cache_policy=NO_CACHE)
def run_cprd_subset_extract_generator(cfg: SubsetConfig) -> subprocess.CompletedProcess:
    """
    Generate Commands
    """
    require_file(_SCRIPT_PATH, 'Generated script')
    corp_path =require_file(cfg.corp_file, 'Corp list file')
    argv = [
        sys.executable,
        str(_SCRIPT_PATH),
        '--corp-file',
        str(corp_path),
        '--mode',
        cfg.mode,
        '--chunk-size',
        str(cfg.chunk_size),
        '--threads',
        str(cfg.threads),
        '--pg-disable-method',
        cfg.pg_disable_method,
    ]
    argv.extend(['--target-connection', cfg.target_connection])
    argv.extend(['--source-connection', cfg.source_connection])
    argv.extend(['--target-schema', cfg.target_schema])
    if cfg.pg_fastload:
        argv.append('--pg-fastload')
    if cfg.include_cp:
        argv.append('--include-cp')
    if cfg.prefix_numeric_bc:
        argv.append('--prefix-numeric-bc')
    out_path = _resolve_master_script_path(cfg.out_master)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argv.extend(['--out', str(out_path)])
    
    return subprocess.run(
        argv,
        cwd=str(_REPO_ROOT),
        capture_output=False,
        text=True,
    )


@task(name='Run-CPRD-Subset-Generator', cache_policy=NO_CACHE)
def run_cprd_subset_extract_generator_original(
    corp_file: str,
    mode: str,
    chunk_size: int,
    threads: int,
    pg_fastload: bool,
    pg_disable_method: str,
    out: str | None,
    include_cp: bool = False,
    target_connection: str = _DEFAULT_TARGET_CONNECTION,
    prefix_numeric_bc: bool = False,
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
    argv.extend(['--target-connection', target_connection])
    if pg_fastload:
        argv.append('--pg-fastload')
    if include_cp:
        argv.append('--include-cp')
    if prefix_numeric_bc:
        argv.append('--prefix-numeric-bc')
    out_path = _resolve_master_script_path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    argv.extend(['--out', str(out_path)])
    
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

@task(name='Refresh-Views', cache_policy=NO_CACHE)
def run_refresh_views(mode: str = 'refresh', targets: str = 'all', schema: str | None = 'public') -> subprocess.CompletedProcess:
    cfg = get_named_config()
    script = require_file(_REFRESH_VIEWS_SCRIPT, 'refresh_colin_extract_views.sh')
    normalized_schema = _normalize_target_schema(schema)
    argv = [
        str(script),
        '--mode', mode,
        '--targets', targets,
        '--db', cfg.DB_NAME_COLIN_MIGR,
        '--host', cfg.DB_HOST_COLIN_MIGR,
        '--port', str(cfg.DB_PORT_COLIN_MIGR),
        '--user', cfg.DB_USER_COLIN_MIGR,
        '--schema', normalized_schema,
    ]
    run_env = dict(os.environ)
    if cfg.DB_PASSWORD_COLIN_MIGR and 'PGPASSWORD' not in run_env:
        run_env['PGPASSWORD'] = cfg.DB_PASSWORD_COLIN_MIGR
    print(f'Running: {" ".join(argv)}')
    return subprocess.run(argv,
                          cwd=str(_REPO_ROOT),
                          capture_output=False,
                          text=True,
                          env=run_env
                          )


@flow(name='Extract-Subset-Flow', log_prints=True, persist_result=False)
def extract_flow(cfg: SubsetConfig) -> None:
    print(f'Running Extract-Subset-Flow with config: {cfg} ')
    """
    Generate files
    """
    if cfg.mode == 'refresh':
        cfg.reset_extract_postgres = False
        print('Running in refresh mode: skipping Postgres DB reset')
    if cfg.reset_extract_postgres:
        cleanup_extract_postgres_db(cfg.target_schema)

    cutoff = get_cuttoff_timestamp(cfg.target_schema)

    config = get_config()
    colin_oracle_engine = colin_oracle_init(config)
    # Get Identifiers
    feed_path: Path | None = None
    if cfg.mode == 'refresh':
        updated_rows = get_updated_identifiers_colin(cutoff_timestamp=cutoff,
                                                     mig_batch_id=config.MIG_BATCH_IDS,
                                                     colin_oracle_engine=colin_oracle_engine,
                                                     chunk_size=cfg.chunk_size,
                                                     scope=cfg.delta_scope)
        print(f'Colin updated identifiers : {len(updated_rows)} rows')
        _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        feed_path = _GENERATED_DIR / f'refresh_corp_feed_{os.getpid()}.tmp'
        seen = set()
        lines = []
        updated_corp_nums = []
        for row in updated_rows:
            for k, v in row.items():
                if k is None or v is None:
                    continue
                if str(k).lower() == 'corp_num':
                    c = str(v).strip()
                    if c and c not in seen:
                        seen.add(c)
                        lines.append(c)
                        updated_corp_nums.append('BC'+c)
                    break
        if not lines:
            raise ValueError('refresh: no corp_num in updated_rows')
        feed_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        corp_file = str(feed_path)
    result: subprocess.CompletedProcess | None = None
    print(f'Running CPRD subset extract generator {cfg.corp_file}')
    try:
        result = run_cprd_subset_extract_generator(cfg)
    finally:
        if feed_path is not None:
            feed_path.unlink(missing_ok=True)
    if result.returncode != 0 and result is not None:
        raise RuntimeError(f'Generator exited with code {result.returncode}')
    print(f'generator completed successfully')
    
    if cfg.run_dbschemacli:
        master_script = _resolve_master_script_path(out=cfg.out_master)
        run_result = run_dbschemacli_task(
            master_script=str(master_script),
            dbschemacli_cmd=cfg.dbschemacli_cmd,
        )
        if run_result.returncode != 0:
            raise RuntimeError(f'DbSchemaCLI exited with code {run_result.returncode}')
    
    print('Running Unfreezing Corps.......')
    run_unfreeze_identifiers(cfg.target_schema)
    
    if cfg.refresh_views and cfg.delta_scope == 'batch':
        refresh_result = run_refresh_views('refresh', 'all', cfg.target_schema)
        if refresh_result.returncode !=0:
            raise RuntimeError(f'Refresh-Views exited with code {refresh_result.returncode}')
    if cfg.mode == 'refresh' and cfg.delta_scope == 'batch':
        prune_identifiers = get_fallen_identifiers(updated_corp_nums)
        prune_fallen_identifiers(prune_identifiers)



@flow(name='Extract-Subset-Flow', log_prints=True, persist_result=False)
def extract_pull_flow(
    corp_file: str,
    mode: str = 'load',
    chunk_size: int = 999,
    threads: int = 4,
    pg_fastload: bool = False,
    pg_disable_method: str = 'table_triggers',
    out: str | None=None,
    run_dbschemacli: bool = False,
    dbschemacli_cmd: str = 'dbschemacli',
    refresh_views: bool = True,
    reset_extract_postgres: bool = True,
    include_cp: bool = False,
    target_connection: str = _DEFAULT_TARGET_CONNECTION,
    delta_scope: str = 'batch',
    target_schema: str = 'colin_extract',
) -> None:
    """
    Generate files
    """
    if mode == 'refresh':
        reset_extract_postgres = False
        print('Running in refresh mode: skipping Postgres DB reset')
    if reset_extract_postgres:
        # cleanup_extract_postgres_db()
        cleanup_extract_postgres_db(target_schema)

    cutoff = get_cuttoff_timestamp(target_schema)

    config = get_config()
    colin_oracle_engine = colin_oracle_init(config)
    # Get Identifiers
    feed_path: Path | None = None
    if mode == 'refresh':
        updated_rows = get_updated_identifiers_colin(cutoff_timestamp=cutoff, mig_batch_id=config.MIG_BATCH_IDS, colin_oracle_engine=colin_oracle_engine, chunk_size=chunk_size, scope=delta_scope)
        print(f'Colin updated identifiers : {len(updated_rows)} rows')
        _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        feed_path = _GENERATED_DIR / f'refresh_corp_feed_{os.getpid()}.tmp'
        seen = set()
        lines = []
        updated_corp_nums = []
        for row in updated_rows:
            for k, v in row.items():
                if k is None or v is None:
                    continue
                if str(k).lower() == 'corp_num':
                    c = str(v).strip()
                    if c and c not in seen:
                        seen.add(c)
                        lines.append(c)
                        updated_corp_nums.append('BC'+c)
                    break
        if not lines:
            raise ValueError('refresh: no corp_num in updated_rows')
        feed_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        corp_file = str(feed_path)
    result: subprocess.CompletedProcess | None = None
    print(f'Running CPRD subset extract generator {corp_file}')
    try:
        result = run_cprd_subset_extract_generator(
            corp_file=corp_file,
            mode=mode,
            chunk_size=chunk_size,
            threads=threads,
            pg_fastload=pg_fastload,
            include_cp=include_cp,
            pg_disable_method=pg_disable_method,
            out=out,
            target_connection=target_connection,
            prefix_numeric_bc=(mode=='refresh'),
        )
    finally:
        if feed_path is not None:
            feed_path.unlink(missing_ok=True)
    if result.returncode != 0 and result is not None:
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
    
    print('Running Unfreezing Corps.......')
    run_unfreeze_identifiers()
    
    if refresh_views and delta_scope == 'batch':
        refresh_result = run_refresh_views('refresh', 'all', target_schema)
        if refresh_result.returncode !=0:
            raise RuntimeError(f'Refresh-Views exited with code {refresh_result.returncode}')
    if mode == 'refresh' and delta_scope == 'batch':
        prune_identifiers = get_fallen_identifiers(updated_corp_nums)
        prune_fallen_identifiers(prune_identifiers)
    
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Run Extract-Pull flow....')
    p.add_argument('--corp_file', default='../data-tool/scripts/generated/corp_ids_ctst.txt', help='Path to newline-delimited corp identifiers')
    p.add_argument('--mode', default='refresh', choices=('refresh', 'load'))
    p.add_argument('--delta-scope', default='batch', choices=('batch', 'full'))
    p.add_argument('--chunk-size', type=int, default=900, help='Max items per IN list.')
    p.add_argument('--threads', type=int, default=4, help='DBSchemaCLI transfer threads')
    p.add_argument('--pg-fastload', action='store_true', help='Enable Postgres fast-load')
    p.add_argument('--include-cp', action='store_true', help='Include corp type CP in subset extract queries')
    p.add_argument('--pg-disable-method', default='table_triggers', choices=('table_triggers', 'replica_role'))
    p.add_argument('--out', default='data-tool/scripts/subset/generated/subset_refresh.sql', help='Output path for generated master script.')
    p.add_argument('--run-dbschemacli', action='store_false')
    p.add_argument('--refresh-views', action='store_false')
    p.add_argument('--dbschemacli-cmd', default='/usr/local/bin/DbSchemaCLI')
    p.add_argument('--reset-extract-postgres', action='store_false')
    p.add_argument('--source-connection', default='ctst')
    p.add_argument('--target-connection', default='ctst_pg')
    p.add_argument('--target-schema', default='public')
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = build_configs(args)
    extract_flow(config)
    # extract_pull_flow(config)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
