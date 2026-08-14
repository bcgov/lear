import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from datetime import datetime
from config import get_named_config
from checks.utils import colin_oracle_init, get_fallout_corp_nums, get_cutoff_timestamp_query, unfreeze_identifiers, get_identifiers_per_batch, corpnum_to_oracle_ids, get_updated_identifiers_for_batch


_DEFAULT_TARGET_CONNECTION = get_named_config().TARGET_CONNECTION
_DEFAULT_TARGET_SCHEMA = get_named_config().TARGET_SCHEMA
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / 'colin-extract-refresh' / 'src' / 'generate_cprd_subset_extract.py'
_GENERATED_DIR = _REPO_ROOT / 'colin-extract-refresh' / 'src' / 'subset' / 'generated'
_SUBSET = _GENERATED_DIR / 'subset_refresh.sql'


def _resolve_master_script_path(out: str | None) -> Path:
    if not out:
        return _SUBSET.resolve()
    p = Path(out).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (_REPO_ROOT / p).resolve()

def require_file(path: str | Path, description: str) -> Path:
    """File Not Found Error"""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f'{description} not found (expected a file): {resolved}')
    return resolved


def get_fallen_identifiers(updated_corp_nums: list) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    if not updated_corp_nums:
        return []
    cfg = get_named_config()
    corp_nums_prune_list_query = get_fallout_corp_nums('SAF', updated_corp_nums, target_schema=cfg.TARGET_SCHEMA)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).connect() as conn:
        result = conn.execute(text(corp_nums_prune_list_query)).scalars().all()
        rows = [str(row).strip() for row in result]
    return rows

def get_cuttoff_timestamp() -> datetime:

    cfg = get_named_config()
    cuttoff_timestamp = get_cutoff_timestamp_query(cfg.TARGET_SCHEMA)
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        cuttoff_timestamp_result = conn.execute(text(cuttoff_timestamp)).scalar()
    print(f"cuttoff timestamp is {cuttoff_timestamp_result}")
    return cuttoff_timestamp_result
    

def run_unfreeze_identifiers() -> None:
    cfg = get_named_config()
    with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).begin() as conn:
        result = conn.execute(text(unfreeze_identifiers(target_schema=cfg.TARGET_SCHEMA)))
    print(f'Unfroze corporation rows={result.rowcount}')

def get_updated_identifiers_colin(cutoff_timestamp: str, mig_batch_id: int, colin_oracle_engine: Engine, chunk_size: int, scope: str) -> list[dict]:
    """
    Get updated corp nums from colin with cutoff timestamp
    """
    cfg = get_named_config()
    corp_list = ''
    if scope == 'batch':
        mig_sql = get_identifiers_per_batch(mig_batch_id, target_schema=cfg.TARGET_SCHEMA)
        with create_engine(cfg.SQLALCHEMY_DATABASE_URI_COLIN_MIGR).connect() as conn:
            row = conn.execute(text(mig_sql)).fetchone()
    
        corp_list = corpnum_to_oracle_ids(row[0]) if row else None    
    colin_sql = get_updated_identifiers_for_batch(cutoff_timestamp, str(corp_list or ''), chunk_size, scope)

    with colin_oracle_engine.connect() as conn:
        result = conn.execute(text(colin_sql))
        rows = [dict(row) for row in result.mappings()]
    return rows

    
def run_cprd_subset_extract_generator(
    corp_file: str,
    mode: str,
    chunk_size: int,
    threads: int,
    pg_fastload: bool,
    pg_disable_method: str,
    out: str | None,
    include_cp: bool = False,
    target_connection: str = _DEFAULT_TARGET_CONNECTION,
    target_schema: str = _DEFAULT_TARGET_SCHEMA,
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
    argv.extend(['--target-schema', target_schema])
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

def extract_pull_flow(
    mode: str = 'load',
    chunk_size: int = 999,
    threads: int = 4,
    pg_fastload: bool = False,
    pg_disable_method: str = 'table_triggers',
    out: str | None=None,
    run_dbschemacli: bool = False,
    dbschemacli_cmd: str = 'dbschemacli',
    include_cp: bool = False,
    target_connection: str = _DEFAULT_TARGET_CONNECTION,
    target_schema: str = _DEFAULT_TARGET_SCHEMA,
    delta_scope: str = 'batch'
) -> None:
    """
    Generate files
    """

    cutoff = get_cuttoff_timestamp()

    config = get_named_config()
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
            target_schema=target_schema,
            prefix_numeric_bc=(mode=='refresh'),
        )
    finally:
        if feed_path is not None:
            feed_path.unlink(missing_ok=True)
    if result.returncode != 0 and result is not None:
        raise RuntimeError(f'Generator exited with code {result.returncode}')
    print(f'generator completed successfully')
    
    # if run_dbschemacli:
    #     master_script = _resolve_master_script_path(out=out)
    #     run_result = run_dbschemacli_task(
    #         master_script=str(master_script),
    #         dbschemacli_cmd=dbschemacli_cmd,
    #     )
    #     if run_result.returncode != 0:
    #         raise RuntimeError(f'DbSchemaCLI exited with code {run_result.returncode}')
    
    # print('Running Unfreezing Corps.......')
    # run_unfreeze_identifiers()
    
    
if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Run Extract-Pull flow....')
    p.add_argument('--mode', default='refresh', choices=('refresh', 'load'))
    p.add_argument('--delta-scope', default='full', choices=('batch', 'full'))
    p.add_argument('--chunk-size', type=int, default=900, help='Max items per IN list.')
    p.add_argument('--threads', type=int, default=4, help='DBSchemaCLI transfer threads')
    p.add_argument('--pg-fastload', action='store_true', help='Enable Postgres fast-load')
    p.add_argument('--include-cp', action='store_true', help='Include corp type CP in subset extract queries')
    p.add_argument('--pg-disable-method', default='table_triggers', choices=('table_triggers', 'replica_role'))
    p.add_argument('--out', default=_SUBSET, help='Output path for generated master script.')
    p.add_argument('--run-dbschemacli', action='store_false')
    p.add_argument('--dbschemacli-cmd', default='dbschemacli')
    p.add_argument('--target-connection', default=_DEFAULT_TARGET_CONNECTION)
    p.add_argument('--target-schema', default=_DEFAULT_TARGET_SCHEMA)
    extract_pull_flow(**vars(p.parse_args()))
