#!/usr/bin/env python3
"""
Generate DbSchemaCLI scripts to extract a subset of COLIN (Oracle CPRD) corps into a Postgres extract DB.

Supports:
- refresh: delete + reload a list of corp identifiers in a target Postgres extract DB
- load:    load only a list of corp identifiers (useful for empty target DBs)

Key constraints handled:
- No Oracle temp tables required.
- Oracle IN-list limit (~1000 items) handled by:
  - chunk_files: execute the full transfer suite per chunk (legacy / best for very large lists), OR
  - or_of_in_lists: execute the transfer suite once using an OR-of-IN-lists predicate (fast for small/medium lists), OR
  - auto: choose or_of_in_lists up to a configurable max-id threshold, else chunk_files.
- Templates remain the source of truth.

Render modes:
- inline (default): parameterization happens at generation time.
  The generator renders chunk SQL scripts and produces a small master script that `execute`s each chunk file.
- vset (legacy): uses DbSchemaCLI vset + &placeholders at runtime. Kept as a fallback.

Outputs (inline mode):
- <out_master>                                  (master DbSchemaCLI script)
- <out_master_stem>_chunks/*.sql                 (chunk scripts)

Then run:
  dbschemacli <out_master>
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


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


@dataclass(frozen=True)
class cfg_GenerationConfig:
    repo_root: Path

    corp_file: Path
    mode: cfg_GenerationMode
    render_mode: cfg_RenderMode

    chunk_size: int
    threads: int
    prefix_numeric_bc: bool
    include_cars: bool

    pg_fastload: bool
    pg_disable_method: cfg_PgDisableMethod

    oracle_in_strategy: cfg_OracleInStrategy
    or_of_in_max_ids: int

    out_master: Path
    out_chunks_dir: Path

    target_connection: str
    target_schema: str


# =========================
# tmpl_* (template specs)
# =========================

TMPL_TOKEN_CORP_IDS = "&corp_ids_in"  # used by delete template (Postgres-side)
TMPL_TOKEN_TARGET_PRED = "&target_corp_num_predicate"  # used by transfer template (Oracle-side)
TMPL_TOKEN_ORACLE_PRED = "&oracle_corp_num_predicate"  # used by transfer template (Oracle-side)


@dataclass(frozen=True)
class tmpl_TemplateSpec:
    name: str
    path: Path
    required_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class tmpl_TemplateBundle:
    disable_triggers: tmpl_TemplateSpec
    enable_triggers: tmpl_TemplateSpec
    pg_boolean_casts: tmpl_TemplateSpec
    pg_fastload_begin: tmpl_TemplateSpec
    pg_fastload_end: tmpl_TemplateSpec
    pg_purge_bcomps_excluded: tmpl_TemplateSpec
    delete_chunk: tmpl_TemplateSpec
    transfer_chunk: tmpl_TemplateSpec
    delete_cars: tmpl_TemplateSpec
    transfer_cars: tmpl_TemplateSpec


# =========================
# chunk_* (chunk planning)
# =========================

@dataclass(frozen=True)
class chunk_ChunkSpec:
    index: int
    total: int
    target_ids: List[str]
    oracle_ids: List[str]
    chunk_file: Path


# =========================
# corp_* (corp id parsing/normalization)
# =========================

BC_PREFIX_RE = re.compile(r"^BC(\d+)$", re.IGNORECASE)


def corp_read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines()


def corp_normalize_target_ids(lines: Iterable[str], *, prefix_numeric_bc: bool) -> List[str]:
    """
    Normalize corp ids for TARGET/Postgres usage:
    - strip whitespace
    - ignore blank lines and comment lines starting with '#'
    - uppercase
    - optionally prefix all-numeric ids with 'BC'
    - de-dupe while preserving order
    """
    out: List[str] = []
    seen: set[str] = set()

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        corp_id = line.upper()

        if prefix_numeric_bc and corp_id.isdigit():
            corp_id = f"BC{corp_id}"

        if corp_id not in seen:
            out.append(corp_id)
            seen.add(corp_id)

    return out


def corp_to_oracle_ids(target_ids: Sequence[str]) -> List[str]:
    """
    Convert TARGET/Postgres corp ids into Oracle corporation.corp_num values.

    For ids like BC0460007 -> 0460007
    Otherwise leave as-is (A1234567 -> A1234567)

    De-dupe while preserving order (avoid wasting Oracle IN-list slots).
    """
    out: List[str] = []
    seen: set[str] = set()

    for target_id in target_ids:
        m = BC_PREFIX_RE.match(target_id)
        oracle_id = m.group(1) if m else target_id

        if oracle_id not in seen:
            out.append(oracle_id)
            seen.add(oracle_id)

    return out


# =========================
# sql_* (SQL rendering helpers)
# =========================

def sql_quote_literal(val: str) -> str:
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def sql_render_in_list(values: Sequence[str], *, multiline: bool = True, indent: str = "    ") -> str:
    """
    Render a comma-separated list of SQL string literals, with NO surrounding parentheses.

    Example (multiline=True):
        'A',
            'B',
            'C'
    """
    quoted = [sql_quote_literal(v) for v in values]
    if not multiline:
        return ",".join(quoted)
    if not quoted:
        return ""
    return (",\n" + indent).join(quoted)


def sql_render_in_predicate(
    column_expr: str,
    values: Sequence[str],
    *,
    max_in_list: int,
    multiline: bool = True,
    indent: str = "    ",
) -> str:
    """
    Render a predicate for Oracle IN-list limits by OR-ing multiple IN(...) clauses as needed.

    Returns SQL like:
      column_expr in ('a','b')
    or:
      (column_expr in (...) OR column_expr in (...))
    """
    if max_in_list <= 0:
        raise ValueError("max_in_list must be > 0")
    if not values:
        # This should never happen for normal runs, but keep it valid SQL.
        return "1=0"

    def _term(vals: Sequence[str]) -> str:
        inner = sql_render_in_list(vals, multiline=multiline, indent=indent)
        if not multiline:
            return f"{column_expr} in ({inner})"
        # indent first element as well
        return f"{column_expr} in (\n{indent}{inner}\n)"

    chunks = [list(values[i:i + max_in_list]) for i in range(0, len(values), max_in_list)]
    terms = [_term(ch) for ch in chunks]
    if len(terms) == 1:
        return terms[0]

    if not multiline:
        return "(" + " OR ".join(terms) + ")"

    joined = "\nOR\n".join(terms)
    return f"(\n{joined}\n)"


# =========================
# tmpl_* (template loading/validation/rendering)
# =========================

def tmpl_default_bundle(repo_root: Path) -> tmpl_TemplateBundle:
    subset_dir = repo_root / "data-tool" / "scripts" / "subset"

    disable_triggers = tmpl_TemplateSpec(
        name="subset_disable_triggers",
        path=subset_dir / "subset_disable_triggers.sql",
    )
    enable_triggers = tmpl_TemplateSpec(
        name="subset_enable_triggers",
        path=subset_dir / "subset_enable_triggers.sql",
    )
    pg_boolean_casts = tmpl_TemplateSpec(
        name="subset_pg_boolean_casts",
        path=subset_dir / "subset_pg_boolean_casts.sql",
    )
    pg_fastload_begin = tmpl_TemplateSpec(
        name="subset_pg_fastload_begin",
        path=subset_dir / "subset_pg_fastload_begin.sql",
    )
    pg_fastload_end = tmpl_TemplateSpec(
        name="subset_pg_fastload_end",
        path=subset_dir / "subset_pg_fastload_end.sql",
    )
    pg_purge_bcomps_excluded = tmpl_TemplateSpec(
        name="subset_pg_purge_bcomps_excluded",
        path=subset_dir / "subset_pg_purge_bcomps_excluded.sql",
    )
    delete_chunk = tmpl_TemplateSpec(
        name="subset_delete_chunk",
        path=subset_dir / "subset_delete_chunk.sql",
        required_tokens=(TMPL_TOKEN_CORP_IDS,),
    )
    transfer_chunk = tmpl_TemplateSpec(
        name="subset_transfer_chunk",
        path=subset_dir / "subset_transfer_chunk.sql",
        required_tokens=(TMPL_TOKEN_TARGET_PRED, TMPL_TOKEN_ORACLE_PRED),
    )
    delete_cars = tmpl_TemplateSpec(
        name="subset_delete_cars",
        path=subset_dir / "subset_delete_cars.sql",
    )
    transfer_cars = tmpl_TemplateSpec(
        name="subset_transfer_cars",
        path=subset_dir / "subset_transfer_cars.sql",
    )

    return tmpl_TemplateBundle(
        disable_triggers=disable_triggers,
        enable_triggers=enable_triggers,
        pg_boolean_casts=pg_boolean_casts,
        pg_fastload_begin=pg_fastload_begin,
        pg_fastload_end=pg_fastload_end,
        pg_purge_bcomps_excluded=pg_purge_bcomps_excluded,
        delete_chunk=delete_chunk,
        transfer_chunk=transfer_chunk,
        delete_cars=delete_cars,
        transfer_cars=transfer_cars,
    )


def tmpl_load_text(spec: tmpl_TemplateSpec) -> str:
    if not spec.path.exists():
        raise SystemExit(f"Missing required template: {spec.name}\nPath: {spec.path}")
    text = spec.path.read_text(encoding="utf-8")
    tmpl_validate_tokens(spec, text)
    return text


def tmpl_validate_tokens(spec: tmpl_TemplateSpec, template_text: str) -> None:
    if not spec.required_tokens:
        return
    missing = [t for t in spec.required_tokens if t not in template_text]
    if missing:
        raise SystemExit(
            "Template token contract violated.\n"
            f"Template: {spec.name}\n"
            f"Path: {spec.path}\n"
            f"Missing required token(s): {', '.join(missing)}\n"
        )


def tmpl_render(template_text: str, *, replacements: Dict[str, str]) -> str:
    out = template_text
    for token, value in replacements.items():
        out = out.replace(token, value)
    return out


# =========================
# chunk_* (chunk planning)
# =========================

def chunk_chunked(items: Sequence[str], size: int) -> List[List[str]]:
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def chunk_plan_chunks(
    target_ids: List[str],
    *,
    chunk_size: int,
    chunks_dir: Path,
    file_stem: str = "chunk",
) -> List[chunk_ChunkSpec]:
    chunks = chunk_chunked(target_ids, chunk_size)
    total = len(chunks)

    out: List[chunk_ChunkSpec] = []
    for idx, chunk_ids in enumerate(chunks, start=1):
        oracle_ids = corp_to_oracle_ids(chunk_ids)
        chunk_file = chunks_dir / f"{file_stem}_{idx:03d}.sql"
        out.append(
            chunk_ChunkSpec(
                index=idx,
                total=total,
                target_ids=chunk_ids,
                oracle_ids=oracle_ids,
                chunk_file=chunk_file,
            )
        )
    return out


# =========================
# gen_* (generation)
# =========================

def gen_write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def gen_build_chunk_sql(
    *,
    chunk: chunk_ChunkSpec,
    mode: cfg_GenerationMode,
    include_delete: bool,
    include_transfer: bool,
    delete_template_text: str,
    transfer_template_text: str,
    corp_ids_sql: str,
    target_predicate_sql: str,
    oracle_predicate_sql: str,
) -> str:
    replacements = {
        TMPL_TOKEN_CORP_IDS: corp_ids_sql,
        TMPL_TOKEN_TARGET_PRED: target_predicate_sql,
        TMPL_TOKEN_ORACLE_PRED: oracle_predicate_sql,
    }

    parts: List[str] = []
    parts.append(f"-- generated chunk script: {chunk.chunk_file.name}")
    parts.append(f"-- mode: {mode.value}")
    parts.append(f"-- chunk: {chunk.index:03d}/{chunk.total:03d}")
    parts.append(f"-- target corps: {len(chunk.target_ids)}")
    parts.append(f"-- oracle corp_num: {len(chunk.oracle_ids)}")
    parts.append("")

    if include_delete and mode == cfg_GenerationMode.REFRESH:
        rendered_delete = tmpl_render(delete_template_text, replacements=replacements)
        if TMPL_TOKEN_CORP_IDS in rendered_delete:
            raise SystemExit(
                f"Internal error: token {TMPL_TOKEN_CORP_IDS} remained after rendering delete template "
                f"for chunk {chunk.index:03d}."
            )
        parts.append(rendered_delete.rstrip())
        parts.append("")

    if include_transfer:
        rendered_transfer = tmpl_render(transfer_template_text, replacements=replacements)
        if TMPL_TOKEN_TARGET_PRED in rendered_transfer or TMPL_TOKEN_ORACLE_PRED in rendered_transfer:
            raise SystemExit(
                f"Internal error: token(s) remained after rendering transfer template for chunk {chunk.index:03d}."
            )
        parts.append(rendered_transfer.rstrip())
        parts.append("")

    return "\n".join(parts)


def gen_write_chunk_files(
    *,
    chunks: Sequence[chunk_ChunkSpec],
    mode: cfg_GenerationMode,
    include_delete: bool,
    include_transfer: bool,
    delete_template_text: str,
    transfer_template_text: str,
    max_in_list: int,
) -> List[Path]:
    out_paths: List[Path] = []
    for ch in chunks:
        corp_ids_sql = sql_render_in_list(ch.target_ids, multiline=True, indent="    ")
        target_predicate_sql = sql_render_in_predicate(
            "target_corp_num",
            ch.target_ids,
            max_in_list=max_in_list,
            multiline=True,
            indent="    ",
        )
        oracle_predicate_sql = sql_render_in_predicate(
            "c.CORP_NUM",
            ch.oracle_ids,
            max_in_list=max_in_list,
            multiline=True,
            indent="    ",
        )

        chunk_sql = gen_build_chunk_sql(
            chunk=ch,
            mode=mode,
            include_delete=include_delete,
            include_transfer=include_transfer,
            delete_template_text=delete_template_text,
            transfer_template_text=transfer_template_text,
            corp_ids_sql=corp_ids_sql,
            target_predicate_sql=target_predicate_sql,
            oracle_predicate_sql=oracle_predicate_sql,
        )
        gen_write_text(ch.chunk_file, chunk_sql)
        out_paths.append(ch.chunk_file)
    return out_paths


def _gen_emit_pg_disable_begin(lines: List[str], *, cfg: cfg_GenerationConfig, templates: tmpl_TemplateBundle) -> None:
    if cfg.pg_disable_method == cfg_PgDisableMethod.TABLE_TRIGGERS:
        lines.append(f"execute {templates.disable_triggers.path.as_posix()}")
        lines.append("")
        return

    if cfg.pg_disable_method == cfg_PgDisableMethod.REPLICA_ROLE:
        lines.append("-- Disable triggers / FK checks for this session (requires superuser privileges).")
        lines.append("SET session_replication_role = replica;")
        lines.append("")
        return

    raise SystemExit(f"Unsupported pg_disable_method: {cfg.pg_disable_method}")


def _gen_emit_pg_disable_end(lines: List[str], *, cfg: cfg_GenerationConfig, templates: tmpl_TemplateBundle) -> None:
    if cfg.pg_disable_method == cfg_PgDisableMethod.TABLE_TRIGGERS:
        lines.append(f"execute {templates.enable_triggers.path.as_posix()}")
        lines.append("")
        return

    if cfg.pg_disable_method == cfg_PgDisableMethod.REPLICA_ROLE:
        lines.append("-- Restore normal trigger behavior for this session.")
        lines.append("SET session_replication_role = origin;")
        lines.append("")
        return

    raise SystemExit(f"Unsupported pg_disable_method: {cfg.pg_disable_method}")


def gen_build_master_script_inline(
    *,
    cfg: cfg_GenerationConfig,
    templates: tmpl_TemplateBundle,
    delete_chunk_files: Sequence[Path],
    transfer_chunk_files: Sequence[Path],
) -> str:
    lines: List[str] = []
    lines.append("vset cli.settings.ignore_errors=false")
    lines.append("vset cli.settings.replace_variables=false")
    lines.append(f"vset cli.settings.transfer_threads={cfg.threads}")
    lines.append("vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'")
    lines.append("vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'")
    lines.append("")
    lines.append(f"connect {cfg.target_connection};")
    lines.append(f"learn schema {cfg.target_schema};")
    lines.append("")

    if cfg.pg_fastload:
        lines.append("-- Postgres fast-load mode (session-level settings)")
        lines.append(f"execute {templates.pg_fastload_begin.path.as_posix()}")
        lines.append("")

    lines.append("-- Postgres helper: allow VARCHAR/BPCHAR -> BOOLEAN assignment (DbSchemaCLI boolean inserts)")
    lines.append(f"execute {templates.pg_boolean_casts.path.as_posix()}")
    lines.append("-- Fail-fast: verify varchar/bpchar -> boolean casts exist")
    lines.append("select 't'::varchar::boolean;")
    lines.append("select 'f'::bpchar::boolean;")
    lines.append("")

    _gen_emit_pg_disable_begin(lines, cfg=cfg, templates=templates)

    if cfg.include_cars:
        lines.append("-- global cars* refresh (not corp-scoped; full dataset truncate + reload)")
        lines.append(f"execute {templates.delete_cars.path.as_posix()}")
        lines.append(f"execute {templates.transfer_cars.path.as_posix()}")
        lines.append("")

    if delete_chunk_files:
        total = len(delete_chunk_files)
        lines.append("-- delete corp-scoped subset (refresh mode)")
        for idx, chunk_file in enumerate(delete_chunk_files, start=1):
            lines.append(f"-- delete chunk {idx:03d}/{total:03d}")
            lines.append(f"execute {chunk_file.as_posix()}")
            lines.append("")
    if transfer_chunk_files:
        total = len(transfer_chunk_files)
        lines.append("-- transfer corp-scoped subset from Oracle to Postgres")
        for idx, chunk_file in enumerate(transfer_chunk_files, start=1):
            lines.append(f"-- transfer chunk {idx:03d}/{total:03d}")
            lines.append(f"execute {chunk_file.as_posix()}")
            lines.append("")

    lines.append("-- purge BCOMPS-excluded corps (computed in Postgres after load)")
    lines.append(f"execute {templates.pg_purge_bcomps_excluded.path.as_posix()}")
    lines.append("")

    _gen_emit_pg_disable_end(lines, cfg=cfg, templates=templates)

    if cfg.pg_fastload:
        lines.append("-- Reset Postgres fast-load session settings")
        lines.append(f"execute {templates.pg_fastload_end.path.as_posix()}")
        lines.append("")

    return "\n".join(lines)


def gen_build_master_script_vset(
    *,
    cfg: cfg_GenerationConfig,
    templates: tmpl_TemplateBundle,
    corp_ids: List[str],
    effective_strategy: cfg_OracleInStrategy,
) -> str:
    """
    vset mode: relies on DbSchemaCLI runtime substitution via vset + cli.settings.replace_variables=true.

    Strategies:
    - chunk_files: delete+transfer per chunk
    - or_of_in_lists: (refresh) delete per chunk, then transfer once using OR-of-IN-lists predicates
                     (load) transfer once using OR-of-IN-lists predicates
    """
    delete_chunks = chunk_chunked(corp_ids, cfg.chunk_size)
    oracle_ids_all = corp_to_oracle_ids(corp_ids)

    lines: List[str] = []
    lines.append("vset cli.settings.ignore_errors=false")
    lines.append("vset cli.settings.replace_variables=true")
    lines.append(f"vset cli.settings.transfer_threads={cfg.threads}")
    lines.append("vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'")
    lines.append("vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'")
    lines.append("")
    lines.append(f"connect {cfg.target_connection};")
    lines.append(f"learn schema {cfg.target_schema};")
    lines.append("")

    if cfg.pg_fastload:
        lines.append("-- Postgres fast-load mode (session-level settings)")
        lines.append(f"execute {templates.pg_fastload_begin.path.as_posix()}")
        lines.append("")

    lines.append("-- Postgres helper: allow VARCHAR/BPCHAR -> BOOLEAN assignment (DbSchemaCLI boolean inserts)")
    lines.append(f"execute {templates.pg_boolean_casts.path.as_posix()}")
    lines.append("-- Fail-fast: verify varchar/bpchar -> boolean casts exist")
    lines.append("select 't'::varchar::boolean;")
    lines.append("select 'f'::bpchar::boolean;")
    lines.append("")

    _gen_emit_pg_disable_begin(lines, cfg=cfg, templates=templates)

    if cfg.include_cars:
        lines.append("-- global cars* refresh (not corp-scoped; full dataset truncate + reload)")
        lines.append(f"execute {templates.delete_cars.path.as_posix()}")
        lines.append(f"execute {templates.transfer_cars.path.as_posix()}")
        lines.append("")

    def _vset_predicates(target_values: Sequence[str], oracle_values: Sequence[str]) -> None:
        target_pred = sql_render_in_predicate(
            "target_corp_num",
            target_values,
            max_in_list=cfg.chunk_size,
            multiline=False,
            indent="",
        )
        oracle_pred = sql_render_in_predicate(
            "c.CORP_NUM",
            oracle_values,
            max_in_list=cfg.chunk_size,
            multiline=False,
            indent="",
        )
        lines.append(f"vset target_corp_num_predicate={target_pred}")
        lines.append(f"vset oracle_corp_num_predicate={oracle_pred}")

    if cfg.mode == cfg_GenerationMode.REFRESH:
        lines.append("-- delete subset (chunked to keep SQL size manageable)")
        total_del = len(delete_chunks)
        for idx, ch in enumerate(delete_chunks, start=1):
            lines.append(f"-- delete chunk {idx:03d}/{total_del:03d} (target corps={len(ch)})")
            lines.append(f"vset corp_ids_in={','.join(sql_quote_literal(v) for v in ch)}")
            lines.append(f"execute {templates.delete_chunk.path.as_posix()}")
            lines.append("")

    if effective_strategy == cfg_OracleInStrategy.OR_OF_IN_LISTS:
        lines.append("-- transfer subset (single pass via OR-of-IN-lists predicate)")
        _vset_predicates(corp_ids, oracle_ids_all)
        lines.append(f"execute {templates.transfer_chunk.path.as_posix()}")
        lines.append("")
    else:
        lines.append("-- transfer subset (chunked)")
        total_tr = len(delete_chunks)
        for idx, ch in enumerate(delete_chunks, start=1):
            oracle_ids = corp_to_oracle_ids(ch)
            lines.append(
                f"-- transfer chunk {idx:03d}/{total_tr:03d} (target corps={len(ch)}, oracle corp_num={len(oracle_ids)})"
            )
            _vset_predicates(ch, oracle_ids)
            lines.append(f"execute {templates.transfer_chunk.path.as_posix()}")
            lines.append("")

    lines.append("-- purge BCOMPS-excluded corps (computed in Postgres after load)")
    lines.append(f"execute {templates.pg_purge_bcomps_excluded.path.as_posix()}")
    lines.append("")

    _gen_emit_pg_disable_end(lines, cfg=cfg, templates=templates)

    if cfg.pg_fastload:
        lines.append("-- Reset Postgres fast-load session settings")
        lines.append(f"execute {templates.pg_fastload_end.path.as_posix()}")
        lines.append("")

    return "\n".join(lines)


# =========================
# cli_* (CLI + orchestration)
# =========================

def cli_parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a chunked DbSchemaCLI subset corp extract script.")
    parser.add_argument("--corp-file", required=True, help="Path to a newline-delimited file of corp identifiers.")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in cfg_GenerationMode],
        default=cfg_GenerationMode.REFRESH.value,
        help="refresh=delete+reload, load=load only (useful for empty target DB).",
    )
    parser.add_argument(
        "--render-mode",
        choices=[m.value for m in cfg_RenderMode],
        default=cfg_RenderMode.INLINE.value,
        help="inline=render per-chunk scripts at generation time; vset=legacy runtime substitution.",
    )
    parser.add_argument(
        "--oracle-in-strategy",
        choices=[m.value for m in cfg_OracleInStrategy],
        default=cfg_OracleInStrategy.AUTO.value,
        help="How to handle Oracle's ~1000 item IN(...) limit. "
             "auto (default)=use or_of_in_lists only when total ids <= --or-of-in-max-ids (default 10000); otherwise chunk_files. "
             "chunk_files=repeat full transfer suite per chunk. "
             "or_of_in_lists=single transfer pass with OR-of-IN-lists predicates.",
    )
    parser.add_argument(
        "--or-of-in-max-ids",
        type=int,
        default=10000,
        help="When --oracle-in-strategy=auto, use or_of_in_lists only if the corp list has <= this many ids (default: 10000). "
             "Example: 30000 ids with default 10000 => chunk_files.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=900,
        help="Max items per IN(...) list. Keep <= 1000 (default: 900). Also used as the per-IN list size for OR-of-IN-lists.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="DbSchemaCLI transfer writer threads (default: 4).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for the generated master DbSchemaCLI script. "
             "Default: data-tool/scripts/generated/subset_<mode>.sql",
    )
    parser.add_argument(
        "--prefix-numeric-bc",
        action="store_true",
        help="If set, any all-numeric corp id lines will be normalized to BC<digits> for the TARGET/Postgres corp_num.",
    )
    parser.add_argument(
        "--no-cars",
        dest="include_cars",
        action="store_false",
        help="Skip global cars* refresh step (carsfile/carsbox/carsrept/carindiv).",
    )
    parser.set_defaults(include_cars=True)

    parser.add_argument(
        "--pg-fastload",
        dest="pg_fastload",
        action="store_true",
        help="Enable Postgres session 'fast load' settings (e.g. synchronous_commit=off) for faster bulk writes.",
    )
    parser.add_argument(
        "--no-pg-fastload",
        dest="pg_fastload",
        action="store_false",
        help="Disable Postgres session 'fast load' settings (default).",
    )
    parser.set_defaults(pg_fastload=False)

    parser.add_argument(
        "--pg-disable-method",
        choices=[m.value for m in cfg_PgDisableMethod],
        default=cfg_PgDisableMethod.TABLE_TRIGGERS.value,
        help="How to suppress triggers during load. "
             "table_triggers=ALTER TABLE ... DISABLE/ENABLE TRIGGER ALL (default). "
             "replica_role=SET session_replication_role=replica|origin (requires superuser; disables triggers/FKs for session).",
    )

    parser.add_argument(
        "--target-connection",
        default="cprd_pg_subset",
        help="DbSchemaCLI connection name for the TARGET Postgres extract DB (default: cprd_pg_subset).",
    )
    parser.add_argument(
        "--target-schema",
        default="public",
        help="Target schema to `learn` in DbSchemaCLI (default: public).",
    )

    return parser.parse_args(argv)


def cfg_resolve_repo_root() -> Path:
    # repo root is two levels above this file: data-tool/scripts/<thisfile>
    return Path(__file__).resolve().parents[2]


def cfg_build_config(args: argparse.Namespace) -> cfg_GenerationConfig:
    repo_root = cfg_resolve_repo_root()

    corp_file = Path(args.corp_file).expanduser().resolve()
    if not corp_file.exists():
        raise SystemExit(f"corp file not found: {corp_file}")

    mode = cfg_GenerationMode(args.mode)
    render_mode = cfg_RenderMode(args.render_mode)

    oracle_in_strategy = cfg_OracleInStrategy(args.oracle_in_strategy)
    or_of_in_max_ids = int(args.or_of_in_max_ids)
    if or_of_in_max_ids <= 0:
        raise SystemExit("--or-of-in-max-ids must be > 0")

    pg_disable_method = cfg_PgDisableMethod(args.pg_disable_method)

    out_master = (
        Path(args.out).expanduser().resolve()
        if args.out
        else (repo_root / "data-tool" / "scripts" / "generated" / f"subset_{mode.value}.sql")
    )
    out_master.parent.mkdir(parents=True, exist_ok=True)

    # Chunk scripts dir is always derived from master output stem for determinism.
    out_chunks_dir = out_master.parent / f"{out_master.stem}_chunks"
    if render_mode == cfg_RenderMode.INLINE:
        out_chunks_dir.mkdir(parents=True, exist_ok=True)

    if args.chunk_size <= 0:
        raise SystemExit("--chunk-size must be > 0")
    if args.threads <= 0:
        raise SystemExit("--threads must be > 0")

    return cfg_GenerationConfig(
        repo_root=repo_root,
        corp_file=corp_file,
        mode=mode,
        render_mode=render_mode,
        chunk_size=int(args.chunk_size),
        threads=int(args.threads),
        prefix_numeric_bc=bool(args.prefix_numeric_bc),
        include_cars=bool(args.include_cars),
        pg_fastload=bool(args.pg_fastload),
        pg_disable_method=pg_disable_method,
        oracle_in_strategy=oracle_in_strategy,
        or_of_in_max_ids=or_of_in_max_ids,
        out_master=out_master,
        out_chunks_dir=out_chunks_dir,
        target_connection=str(args.target_connection),
        target_schema=str(args.target_schema),
    )


def _effective_oracle_strategy(cfg: cfg_GenerationConfig, total_ids: int) -> cfg_OracleInStrategy:
    if cfg.oracle_in_strategy != cfg_OracleInStrategy.AUTO:
        return cfg.oracle_in_strategy
    return cfg_OracleInStrategy.OR_OF_IN_LISTS if total_ids <= cfg.or_of_in_max_ids else cfg_OracleInStrategy.CHUNK_FILES


def run(cfg: cfg_GenerationConfig) -> int:
    templates = tmpl_default_bundle(cfg.repo_root)

    # Load/validate templates we depend on (fail fast if template contract changes).
    delete_template_text = tmpl_load_text(templates.delete_chunk)
    transfer_template_text = tmpl_load_text(templates.transfer_chunk)

    # Ensure the execute-only templates exist too (even though we don't render them).
    for spec in (
        templates.disable_triggers,
        templates.enable_triggers,
        templates.pg_boolean_casts,
        templates.pg_fastload_begin,
        templates.pg_fastload_end,
        templates.pg_purge_bcomps_excluded,
        templates.delete_cars,
        templates.transfer_cars,
    ):
        if not spec.path.exists():
            raise SystemExit(f"Missing required template: {spec.name}\nPath: {spec.path}")

    # Parse & normalize corp ids.
    target_ids = corp_normalize_target_ids(
        corp_read_lines(cfg.corp_file),
        prefix_numeric_bc=cfg.prefix_numeric_bc,
    )
    if not target_ids:
        raise SystemExit("No corp ids found after parsing (file empty or only comments).")

    effective_strategy = _effective_oracle_strategy(cfg, total_ids=len(target_ids))

    if cfg.render_mode == cfg_RenderMode.INLINE:
        delete_files: List[Path] = []
        transfer_files: List[Path] = []

        if effective_strategy == cfg_OracleInStrategy.CHUNK_FILES:
            chunks = chunk_plan_chunks(target_ids, chunk_size=cfg.chunk_size, chunks_dir=cfg.out_chunks_dir, file_stem="chunk")
            combined_files = gen_write_chunk_files(
                chunks=chunks,
                mode=cfg.mode,
                include_delete=(cfg.mode == cfg_GenerationMode.REFRESH),
                include_transfer=True,
                delete_template_text=delete_template_text,
                transfer_template_text=transfer_template_text,
                max_in_list=cfg.chunk_size,
            )
            transfer_files = combined_files

        else:
            # OR-of-IN-lists: transfer once using predicates; keep deletes chunked in refresh mode.
            if cfg.mode == cfg_GenerationMode.REFRESH:
                del_chunks = chunk_plan_chunks(target_ids, chunk_size=cfg.chunk_size, chunks_dir=cfg.out_chunks_dir, file_stem="delete_chunk")
                delete_files = gen_write_chunk_files(
                    chunks=del_chunks,
                    mode=cfg.mode,
                    include_delete=True,
                    include_transfer=False,
                    delete_template_text=delete_template_text,
                    transfer_template_text=transfer_template_text,
                    max_in_list=cfg.chunk_size,
                )

            oracle_ids_all = corp_to_oracle_ids(target_ids)
            transfer_chunk = chunk_ChunkSpec(
                index=1,
                total=1,
                target_ids=target_ids,
                oracle_ids=oracle_ids_all,
                chunk_file=cfg.out_chunks_dir / "transfer_all.sql",
            )
            transfer_files = gen_write_chunk_files(
                chunks=[transfer_chunk],
                mode=cfg.mode,
                include_delete=False,
                include_transfer=True,
                delete_template_text=delete_template_text,
                transfer_template_text=transfer_template_text,
                max_in_list=cfg.chunk_size,
            )

        master_text = gen_build_master_script_inline(
            cfg=cfg,
            templates=templates,
            delete_chunk_files=delete_files,
            transfer_chunk_files=transfer_files,
        )
        gen_write_text(cfg.out_master, master_text)

        n_ids = len(target_ids)
        in_groups = (n_ids + cfg.chunk_size - 1) // cfg.chunk_size

        print(f"Wrote master script: {cfg.out_master}")
        if cfg.out_chunks_dir.exists():
            print(f"Wrote chunk scripts:  {cfg.out_chunks_dir}")
        print("")
        print("Run:")
        print(f"  dbschemacli {cfg.out_master}")
        print("")
        print("Notes:")
        print(" - Corp ids in the file should match the TARGET Postgres extract corp_num format (e.g. BC0460007).")
        print(" - If you have numeric-only corp ids, consider --prefix-numeric-bc.")
        print(f" - corp ids: {n_ids} => ceil({n_ids}/{cfg.chunk_size}) = {in_groups} chunk(s)")
        print(f" - Oracle IN-list handling: {effective_strategy.value} (configured: {cfg.oracle_in_strategy.value})")
        print(f" - chunk-size (max items per IN list): {cfg.chunk_size}")
        if effective_strategy == cfg_OracleInStrategy.CHUNK_FILES:
            print(f" - transfer suite executions: {in_groups} (one per chunk file)")
        else:
            print(" - transfer suite executions: 1 (single pass via OR-of-IN-lists)")
            print(f" - OR-of-IN-lists groups: {in_groups} (each IN list <= {cfg.chunk_size} ids)")
            if cfg.mode == cfg_GenerationMode.REFRESH:
                print(f" - delete chunks (refresh mode): {in_groups} (always chunked)")
        if cfg.oracle_in_strategy == cfg_OracleInStrategy.AUTO:
            print(f" - auto threshold (--or-of-in-max-ids): {cfg.or_of_in_max_ids}")
        if cfg.include_cars:
            print(" - cars* tables will be globally refreshed (truncate + reload from Oracle).")
        else:
            print(" - cars* tables will NOT be refreshed (--no-cars was set).")
        print(f" - Postgres fast-load session settings: {'ENABLED' if cfg.pg_fastload else 'disabled'} (--pg-fastload)")
        print(f" - Postgres trigger suppression: {cfg.pg_disable_method.value} (--pg-disable-method)")
        if cfg.pg_disable_method == cfg_PgDisableMethod.REPLICA_ROLE:
            print("   - NOTE: replica_role requires superuser and disables triggers/FKs for the session.")
        return 0

    # vset mode: generate only a master script (no chunk files)
    master_text = gen_build_master_script_vset(
        cfg=cfg,
        templates=templates,
        corp_ids=target_ids,
        effective_strategy=effective_strategy,
    )
    gen_write_text(cfg.out_master, master_text)

    n_ids = len(target_ids)
    in_groups = (n_ids + cfg.chunk_size - 1) // cfg.chunk_size

    print(f"Wrote (vset mode): {cfg.out_master}")
    print("")
    print("Run:")
    print(f"  dbschemacli {cfg.out_master}")
    print("")
    print("Notes:")
    print(" - This script relies on DbSchemaCLI vset variables and runtime substitution.")
    print(f" - corp ids: {n_ids} => ceil({n_ids}/{cfg.chunk_size}) = {in_groups} chunk(s)")
    print(f" - Oracle IN-list handling: {effective_strategy.value} (configured: {cfg.oracle_in_strategy.value})")
    print(f" - chunk-size (max items per IN list): {cfg.chunk_size}")
    if effective_strategy == cfg_OracleInStrategy.CHUNK_FILES:
        print(f" - transfer suite executions: {in_groups} (looped in SQL via vset/while)")
    else:
        print(" - transfer suite executions: 1 (single pass via OR-of-IN-lists)")
        print(f" - OR-of-IN-lists groups: {in_groups} (each IN list <= {cfg.chunk_size} ids)")
        if cfg.mode == cfg_GenerationMode.REFRESH:
            print(f" - delete chunks (refresh mode): {in_groups} (looped in SQL)")
    if cfg.oracle_in_strategy == cfg_OracleInStrategy.AUTO:
        print(f" - auto threshold (--or-of-in-max-ids): {cfg.or_of_in_max_ids}")
    print(" - Prefer --render-mode inline for faster runs (inline generates static SQL per chunk).")
    print(f" - Postgres fast-load session settings: {'ENABLED' if cfg.pg_fastload else 'disabled'} (--pg-fastload)")
    print(f" - Postgres trigger suppression: {cfg.pg_disable_method.value} (--pg-disable-method)")
    if cfg.pg_disable_method == cfg_PgDisableMethod.REPLICA_ROLE:
        print("   - NOTE: replica_role requires superuser and disables triggers/FKs for the session.")
    return 0


def main() -> int:
    args = cli_parse_args()
    cfg = cfg_build_config(args)
    return run(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
