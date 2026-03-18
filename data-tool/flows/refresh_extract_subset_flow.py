import argparse
from pathlib import Path
import subprocess
import sys
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.states import Failed

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / 'data-tool' / 'scripts' / 'generate_cprd_subset_extract.py'

def _script_exists() -> None:
    if not _SCRIPT_PATH.exists():
        raise FileNotFoundError(
            f'CPRD subset extract script not found: {_SCRIPT_PATH}'
        )

@task(name='Run-CPRD-Subset-Generator', cache_policy=NO_CACHE)
def run_cprd_subset_extract_generator(
        corp_file: str,
        mode: str = 'load',
        chunk_size: int = 500,
        threads: int = 4,
        pg_fastload: bool = False,
        pg_disabled_method: str = 'replica_role',
        out: str | None = None
) -> subprocess.CompletedProcess:
    """
    Generate Commands
    """
    _script_exists()
    corp_path = Path(corp_file).expanduser().resolve()
    if not corp_path.exists():
        raise FileNotFoundError(f'Corp file not found: {corp_path}')
    
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
        pg_disabled_method,
    ]
    if pg_fastload:
        argv.append('--pg-fastload')
    if out is not None:
        argv.extend(['--out', str(Path(out).expanduser().resolve())])
    
    result = subprocess.run(
        argv,
        cwd=str(_REPO_ROOT),
        capture_output=False,
        text=True
    )
    return result


@flow(name='Extract-Subset-Flow', log_prints=True, persist_result=False)
def extract_pull_flow(
    corp_file : str,
    mode: str = 'load',
    chunk_size: int = 900,
    threads: int = 4,
    pg_fastload: bool = False,
    pg_disable_method: str = 'replica_role',
    out: str | None=None,
):
    """
    Generate files
    """
    try:
        print(f'Running CPRD subset extract generator {corp_file}')
        result = run_cprd_subset_extract_generator(
            corp_file=corp_file,
            mode=mode,
            chunk_size=chunk_size,
            threads=threads,
            pg_fastload=pg_fastload,
            pg_disabled_method=pg_disable_method,
            out=out,
        )
        if result.returncode != 0:
            print(f'generator exited with code {result.returncode}')
            return Failed(message=f'CPRD subset extract generator exited with code {result.returncode}.')
        print(f'generator completed successfully')
    except Exception as e:
        raise e
    

    if __name__ == '__main__':
        p = argparse.ArgumentParser(description='Run Extract-Pull flow....')
        p.add_argument('corp_file', help='Path to newline-delimited corp identifiers')
        p.add_argument('--mode', default='load', choices=('refresh', 'load'))
        p.add_argument('--chunk-size', type=int, default=900, help='Max items per IN list.')
        p.add_argument('--threads', type=int, default=4, help='DBSchemaCLI transfer threads')
        p.add_argument('--pg-fastload', action='store_true', help='Enable Postgres fast-load')
        p.add_argument('--pg-disable-method', default='reploca_role', choices=('table_triggers', 'replica_role'))
        p.add_argument('--out', default=None, help='Output path for generated master script.')
        args = p.parse_args()
        sys.exit(extract_pull_flow(
            corp_file=args.corp_file,
            mode=args.mode,
            chunk_size=args.chunk_size,
            threads=args.threads,
            pg_fastload=args.pg_fastload,
            pg_disable_method=args.pg_disable_method,
            out=args.out,
        ))