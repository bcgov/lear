from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import get_named_config
from common.colin_queries import get_identifiers_per_batch, get_updated_identifiers_for_batch
from common.init_utils import colin_oracle_init, get_config
from common.query_utils import (
    corpnum_to_oracle_ids,
    get_cutoff_timestamp_query,
    get_fallout_corp_nums,
    prune_candidates_from_account,
    prune_candidates_from_batch,
    prune_candidates_from_cp,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / 'data-tool' / 'scripts' / 'generate_cprd_subset_extract.py'
_GENERATED_DIR = _REPO_ROOT / 'data-tool' / 'scripts' / 'generated'
_DEFAULT_DDL = _REPO_ROOT / 'data-tool' / 'scripts' / 'colin_corps_extract_postgres_ddl'
_SUBSET = _GENERATED_DIR / 'subset_refresh.sql'
_REFRESH_VIEWS_SCRIPT = _REPO_ROOT / 'data-tool' / 'refresh_colin_extract_views.sh'
_BUILD_VIEWS_SCRIPT = _REPO_ROOT / 'data-tool' / 'scripts' / 'colin_corps_extract_postgres_views_ddl'


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError('must be a positive integer') from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return parsed


def _resolve_master_script_path(out: str | None) -> Path:
    if not out:
        return _SUBSET.resolve()
    p = Path(out).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (_REPO_ROOT / p).resolve()


def _resolve_artifact_dir(artifact_dir: str | None) -> Path | None:
    if not artifact_dir:
        return None
    path = Path(artifact_dir).expanduser()
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path.resolve()


def _default_out_for_artifact(artifact_dir: str | None, mode: str, out: str | None) -> str | None:
    if out:
        return out
    artifact_path = _resolve_artifact_dir(artifact_dir)
    if artifact_path is None:
        return None
    return str(artifact_path / f'subset_{mode}.sql')


def _normalize_target_corp_num(value: object) -> str | None:
    corp_num = str(value).strip().upper()
    if not corp_num:
        return None
    if corp_num.isdigit():
        return f'BC{corp_num}'
    return corp_num


def _extract_refresh_corp_nums(updated_rows: list[dict]) -> tuple[list[str], list[str]]:
    feed_lines: list[str] = []
    updated_corp_nums: list[str] = []
    seen: set[str] = set()
    for row in updated_rows:
        for key, value in row.items():
            if key is None or value is None:
                continue
            if str(key).lower() != 'corp_num':
                continue
            feed_value = str(value).strip().upper()
            target_value = _normalize_target_corp_num(feed_value)
            if feed_value and target_value and target_value not in seen:
                seen.add(target_value)
                feed_lines.append(feed_value)
                updated_corp_nums.append(target_value)
            break
    return feed_lines, updated_corp_nums


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
    _run_cmd(['psql', *pg_flags, '-d', 'postgres', '-c', terminate_sql], env=run_env)
    _run_cmd(['dropdb', *pg_flags, '--maintenance-db=postgres', '--if-exists', dbname], env=run_env)
    _run_cmd(['createdb', *pg_flags, '--maintenance-db=postgres', '-T', 'template0', dbname], env=run_env)
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', '-f', str(_DEFAULT_DDL)], env=run_env)
    _run_cmd(['psql', *pg_flags, '-d', dbname, '-v', 'ON_ERROR_STOP=1', '-f', str(_BUILD_VIEWS_SCRIPT)], env=run_env)


@task(name='Get-Fallen-Out-Identifiers', cache_policy=NO_CACHE)
def get_fallen_identifiers(updated_corp_nums: list) -> list[str]:
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
def prune_fallen_identifiers(fallen_out_identifiers_list: list) -> None:
    """
    Prune fallen-out corp nums from migration candidate tables.
    """
    if not fallen_out_identifiers_list:
        print('No fallout corps to prune')
        return
    cfg = get_named_config()
    cp_query = prune_candidates_from_cp(fallen_out_identifiers_list)
    batch_query = prune_candidates_from_batch(fallen_out_identifiers_list)
    account_query = prune_candidates_from_account(fallen_out_identifiers_list)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        prune_cp = conn.execute(text(cp_query))
        prune_batch = conn.execute(text(batch_query))
        prune_account = conn.execute(text(account_query))
    print(f'Pruned corp_processing={prune_cp.rowcount}, mig_corp_batch={prune_batch.rowcount}, mig_corp_account={prune_account.rowcount}')


def get_cuttoff_timestamp():
    cfg = get_named_config()
    cuttoff_timestamp = get_cutoff_timestamp_query()
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        cuttoff_timestamp_result = conn.execute(text(cuttoff_timestamp)).scalar()
    print(f'cuttoff timestamp is {cuttoff_timestamp_result}')
    return cuttoff_timestamp_result


@task(name='Cleanup-Extract-Postgres', cache_policy=NO_CACHE)
def cleanup_extract_postgres_db() -> None:
    _reset_extract_postgres_db()


@task(name='Get-Updated-Identifiers-Colin', cache_policy=NO_CACHE)
def get_updated_identifiers_colin(
    cutoff_timestamp: str,
    mig_batch_id: int,
    colin_oracle_engine: Engine,
    chunk_size: int = 900,
    lookback_hours: int = 5,
) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    cfg = get_named_config()
    mig_sql = get_identifiers_per_batch(mig_batch_id)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).connect() as conn:
        row = conn.execute(text(mig_sql)).fetchone()

    corp_list = corpnum_to_oracle_ids(row[0]) if row and row[0] else None
    if not corp_list:
        raise ValueError(f'no corp identifiers found for mig_batch_id={mig_batch_id}')

    colin_sql = get_updated_identifiers_for_batch(
        cutoff_timestamp,
        corp_list,
        chunk_size=chunk_size,
        lookback_hours=lookback_hours,
    )

    with colin_oracle_engine.connect() as conn:
        result = conn.execute(text(colin_sql))
        rows = [dict(row) for row in result.mappings()]
    return rows


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
    include_cars: bool = False,
    source_connection: str = 'cprd',
    target_connection: str = 'ctst_pg',
    target_schema: str = 'public',
    prefix_numeric_bc: bool = False,
) -> subprocess.CompletedProcess:
    """
    Generate Commands
    """
    require_file(_SCRIPT_PATH, 'Generated script')
    corp_path = require_file(corp_file, 'Corp list file')

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
        '--source-connection',
        source_connection,
        '--target-connection',
        target_connection,
        '--target-schema',
        target_schema,
    ]
    argv.append('--include-cars' if include_cars else '--no-cars')
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
def run_refresh_views(mode: str = 'refresh', targets: str = 'all') -> subprocess.CompletedProcess:
    cfg = get_named_config()
    script = require_file(_REFRESH_VIEWS_SCRIPT, 'refresh_colin_extract_views.sh')
    argv = [
        str(script),
        '--mode', mode,
        '--targets', targets,
        '--db', cfg.DB_NAME_COLIN_MIGR,
        '--host', cfg.DB_HOST_COLIN_MIGR,
        '--port', str(cfg.DB_PORT_COLIN_MIGR),
        '--user', cfg.DB_USER_COLIN_MIGR,
    ]
    run_env = dict(os.environ)
    if cfg.DB_PASSWORD_COLIN_MIGR and 'PGPASSWORD' not in run_env:
        run_env['PGPASSWORD'] = cfg.DB_PASSWORD_COLIN_MIGR
    print(f'Running: {" ".join(argv)}')
    return subprocess.run(
        argv,
        cwd=str(_REPO_ROOT),
        capture_output=False,
        text=True,
        env=run_env,
    )


@flow(name='Extract-Subset-Flow', log_prints=True, persist_result=False)
def extract_pull_flow(
    corp_file: str | None = None,
    mode: str = 'refresh',
    chunk_size: int = 900,
    threads: int = 4,
    pg_fastload: bool = False,
    pg_disable_method: str = 'table_triggers',
    out: str | None = None,
    run_dbschemacli: bool = False,
    dbschemacli_cmd: str = 'dbschemacli',
    refresh_views: bool = False,
    reset_extract_postgres: bool = True,
    include_cp: bool = False,
    include_cars: bool = False,
    source_connection: str = 'cprd',
    target_connection: str = 'ctst_pg',
    target_schema: str = 'public',
    mig_batch_id: int = 1,
    lookback_hours: int = 5,
    artifact_dir: str | None = None,
) -> None:
    """
    Generate files
    """
    if mode == 'load' and not corp_file:
        raise ValueError('load mode requires --corp-file')
    if mode == 'refresh':
        reset_extract_postgres = False
        print('Running in refresh mode: skipping Postgres DB reset')
    if reset_extract_postgres:
        cleanup_extract_postgres_db()

    artifact_path = _resolve_artifact_dir(artifact_dir)
    if artifact_path is not None:
        artifact_path.mkdir(parents=True, exist_ok=True)
    out = _default_out_for_artifact(artifact_dir, mode, out)

    feed_path: Path | None = None
    delete_feed = False
    updated_corp_nums: list[str] = []
    if mode == 'refresh' and not corp_file:
        cutoff = get_cuttoff_timestamp()
        config = get_config()
        colin_oracle_engine = colin_oracle_init(config)
        updated_rows = get_updated_identifiers_colin(
            cutoff_timestamp=cutoff,
            mig_batch_id=mig_batch_id,
            colin_oracle_engine=colin_oracle_engine,
            chunk_size=chunk_size,
            lookback_hours=lookback_hours,
        )
        print(f'Colin updated identifiers : {len(updated_rows)} rows')
        feed_lines, updated_corp_nums = _extract_refresh_corp_nums(updated_rows)
        if not feed_lines:
            print(
                'Refresh found no updated corp identifiers to extract; '
                'skipping generator, DbSchemaCLI, pruning, and materialized-view refresh.'
            )
            return
        if artifact_path is not None:
            feed_path = artifact_path / f'refresh_corp_feed_{os.getpid()}_{uuid4().hex}.txt'
        else:
            _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
            feed_path = _GENERATED_DIR / f'refresh_corp_feed_{os.getpid()}.tmp'
            delete_feed = True
        feed_path.write_text('\n'.join(feed_lines) + '\n', encoding='utf-8')
        corp_file = str(feed_path)
    elif mode == 'refresh' and corp_file:
        updated_corp_nums = [
            normalized
            for line in Path(corp_file).read_text(encoding='utf-8').splitlines()
            if (normalized := _normalize_target_corp_num(line))
        ]

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
            include_cars=include_cars,
            pg_disable_method=pg_disable_method,
            out=out,
            source_connection=source_connection,
            target_connection=target_connection,
            target_schema=target_schema,
            prefix_numeric_bc=(mode == 'refresh'),
        )
    finally:
        if feed_path is not None and delete_feed:
            feed_path.unlink(missing_ok=True)
    if result is not None and result.returncode != 0:
        raise RuntimeError(f'Generator exited with code {result.returncode}')
    print('generator completed successfully')

    if run_dbschemacli:
        master_script = _resolve_master_script_path(out=out)
        run_result = run_dbschemacli_task(
            master_script=str(master_script),
            dbschemacli_cmd=dbschemacli_cmd,
        )
        if run_result.returncode != 0:
            raise RuntimeError(f'DbSchemaCLI exited with code {run_result.returncode}')

    if refresh_views:
        refresh_result = run_refresh_views('refresh', 'all')
        if refresh_result.returncode != 0:
            raise RuntimeError(f'Refresh-Views exited with code {refresh_result.returncode}')
    if mode == 'refresh' and run_dbschemacli and updated_corp_nums:
        prune_identifiers = get_fallen_identifiers(updated_corp_nums)
        prune_fallen_identifiers(prune_identifiers)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='Run Extract-Pull flow....')
    p.add_argument('--corp-file', '--corp_file', dest='corp_file', default=None, help='Path to newline-delimited corp identifiers')
    p.add_argument('--mode', default='refresh', choices=('refresh', 'load'))
    p.add_argument('--chunk-size', type=_positive_int, default=900, help='Max items per IN list.')
    p.add_argument('--threads', type=_positive_int, default=4, help='DBSchemaCLI transfer threads')
    p.add_argument('--pg-fastload', action='store_true', help='Enable Postgres fast-load')
    p.add_argument('--include-cp', action='store_true', help='Include corp type CP in subset extract queries')
    p.add_argument('--include-cars', dest='include_cars', action='store_true', help='Include global cars* refresh')
    p.add_argument('--no-cars', dest='include_cars', action='store_false', help='Skip global cars* refresh')
    p.set_defaults(include_cars=False)
    p.add_argument('--pg-disable-method', default='table_triggers', choices=('table_triggers', 'replica_role'))
    p.add_argument('--out', default=None, help='Output path for generated master script.')
    p.add_argument('--artifact-dir', default=None, help='Directory for retained run artifacts/replay feed and default generated master script')
    p.add_argument('--run-dbschemacli', action='store_true', default=False, help='Run DbSchemaCLI after generating the master script')
    p.add_argument('--refresh-views', dest='refresh_views', action='store_true', help='Refresh materialized views from this flow (normally handled by the OCP wrapper)')
    p.add_argument('--no-refresh-views', dest='refresh_views', action='store_false', help='Do not refresh materialized views from this flow')
    p.set_defaults(refresh_views=False)
    p.add_argument('--dbschemacli-cmd', default='dbschemacli')
    p.add_argument('--reset-extract-postgres', dest='reset_extract_postgres', action='store_true', help='Reset/rebuild extract Postgres before load mode')
    p.add_argument('--no-reset-extract-postgres', dest='reset_extract_postgres', action='store_false', help='Do not reset/rebuild extract Postgres')
    p.set_defaults(reset_extract_postgres=True)
    p.add_argument('--source-connection', default='cprd')
    p.add_argument('--target-connection', default='ctst_pg')
    p.add_argument('--target-schema', default='public')
    p.add_argument('--mig-batch-id', type=_positive_int, default=1)
    p.add_argument('--lookback-hours', type=_positive_int, default=5)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    extract_pull_flow(**vars(args))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
