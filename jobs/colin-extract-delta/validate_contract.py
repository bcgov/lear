#!/usr/bin/env python3
"""Lightweight OCP job contract checks that do not require pytest."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


JOB_DIR = Path(__file__).resolve().parent
REPO_ROOT = JOB_DIR.parents[1]
DATA_TOOL_DIR = REPO_ROOT / "data-tool"
FLOW_PATH = DATA_TOOL_DIR / "flows" / "refresh_extract_subset_flow.py"
GENERATOR_PATH = DATA_TOOL_DIR / "scripts" / "generate_cprd_subset_extract.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_flow_parser_contract() -> None:
    """Verify the OCP run.sh flags still parse when flow deps are available."""
    sys.path.insert(0, str(DATA_TOOL_DIR / "flows"))
    try:
        flow_module = _load_module("refresh_extract_subset_flow_contract", FLOW_PATH)
    except ImportError as err:
        print(f"flow parser contract: skipped (missing import dependency: {err})")
        return

    with tempfile.TemporaryDirectory(prefix="colin-extract-contract-") as tmp:
        artifact_dir = Path(tmp)
        out = artifact_dir / "subset_refresh.sql"
        argv = [
            "--mode",
            "refresh",
            "--chunk-size",
            "900",
            "--threads",
            "4",
            "--pg-disable-method",
            "table_triggers",
            "--artifact-dir",
            str(artifact_dir),
            "--out",
            str(out),
            "--run-dbschemacli",
            "--dbschemacli-cmd",
            "dbschemacli",
            "--source-connection",
            "cpqa",
            "--target-connection",
            "ocp_pg",
            "--target-schema",
            "extract_delta",
            "--mig-batch-id",
            "1",
            "--lookback-hours",
            "5",
            "--no-cars",
            "--no-reset-extract-postgres",
        ]
        args = flow_module.build_arg_parser().parse_args(argv)
        assert args.mode == "refresh"
        assert args.artifact_dir == str(artifact_dir)
        assert args.out == str(out)
        assert args.run_dbschemacli is True
        assert args.include_cars is False
        assert args.reset_extract_postgres is False
        assert args.source_connection == "cpqa"
        assert args.target_connection == "ocp_pg"
        assert args.target_schema == "extract_delta"
    print("flow parser contract: ok")


def validate_generator_rendering_contract() -> None:
    generator = _load_module("generate_cprd_subset_extract_contract", GENERATOR_PATH)
    with tempfile.TemporaryDirectory(prefix="colin-extract-generator-") as tmp:
        tmp_path = Path(tmp)
        corp_file = tmp_path / "corps.txt"
        out = tmp_path / "subset_refresh.sql"
        corp_file.write_text("BC1234567\n", encoding="utf-8")

        args = generator.cli_parse_args(
            [
                "--corp-file",
                str(corp_file),
                "--mode",
                "refresh",
                "--oracle-in-strategy",
                "or_of_in_lists",
                "--source-connection",
                "cpqa",
                "--target-connection",
                "ocp_pg",
                "--target-schema",
                "extract_delta",
                "--out",
                str(out),
            ]
        )
        cfg = generator.cfg_build_config(args)
        rc = generator.run(cfg)
        if rc != 0:
            raise AssertionError(f"generator returned {rc}")

        sql_files = sorted(tmp_path.rglob("*.sql"))
        if not sql_files:
            raise AssertionError("generator did not produce SQL files")
        combined_sql = "\n".join(path.read_text(encoding="utf-8") for path in sql_files)
        lower_sql = combined_sql.lower()
        master_sql = out.read_text(encoding="utf-8")

        checks = {
            "connect ocp_pg;": "target alias was not rendered in master SQL",
            "learn schema extract_delta;": "target schema learn command was not rendered",
            "transfer extract_delta.corporation from cpqa using": "source alias/target schema transfer was not rendered",
        }
        for needle, message in checks.items():
            haystack = lower_sql if needle.startswith("transfer") else master_sql
            if needle not in haystack:
                raise AssertionError(message)
        if "__dbschema_" in lower_sql:
            raise AssertionError("generated SQL contains unresolved __DBSCHEMA_*__ token")
        if " from cprd" in lower_sql:
            raise AssertionError("generated SQL contains unexpected hardcoded source alias 'cprd'")
        if "public." in lower_sql:
            raise AssertionError("generated SQL contains unexpected hardcoded target schema 'public.'")
        print(f"generator rendering contract: ok ({len(sql_files)} SQL files)")


def main() -> int:
    validate_flow_parser_contract()
    validate_generator_rendering_contract()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
