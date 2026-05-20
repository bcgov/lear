"""Read-only verifier flow for COLIN update verification.

This module implements shared configuration validation, COLIN extract
candidate-selection query helpers, Oracle read-back verification, CSV report
generation, and Prefect orchestration for the Verify COLIN Updates flow.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.init_utils import colin_extract_init, colin_oracle_init, get_config
from colin_freeze_flow import ORACLE_IN_LIMIT, build_in_bind_clause, convert_to_colin_format
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, bindparam, text
from sqlalchemy.sql.elements import TextClause

FLOW_NAME = "verify-colin-updates-flow"

CHECK_FREEZE = "freeze"
CHECK_EARLY_ADOPTER = "early_adopter"
CHECK_AR_IND_IS_NO = "ar_ind_is_no"

_CHECK_CONFIG_ATTRS = {
    CHECK_FREEZE: "VERIFY_COLIN_UPDATES_CHECK_FREEZE",
    CHECK_EARLY_ADOPTER: "VERIFY_COLIN_UPDATES_CHECK_EARLY_ADOPTER",
    CHECK_AR_IND_IS_NO: "VERIFY_COLIN_UPDATES_CHECK_AR_IND_IS_NO",
}

EXPECTED_FREEZE_TYP_CD = "C"
EXPECTED_IN_EARLY_ADOPTER = True
EXPECTED_SEND_AR_IND_IS_NO = "N"

ORACLE_READ_BACK_QUERY = """
    SELECT
        c.corp_num,
        c.corp_frozen_typ_cd,
        c.SEND_AR_IND,
        CASE WHEN cea.corp_num IS NULL THEN 0 ELSE 1 END AS in_early_adopter
    FROM corporation c
    LEFT JOIN corp_early_adopters cea ON cea.corp_num = c.corp_num
    WHERE c.corp_num IN {corp_nums}
"""

SUMMARY_FIELDNAMES = [
    "total_count",
    "success_count",
    "failure_count",
]

_DETAIL_BASE_FIELDNAMES = [
    "original_corp_num",
    "colin_corp_num",
    "oracle_found",
    "mismatch_checks",
]

_DETAIL_CHECK_FIELDNAMES = [
    "actual_corp_frozen_typ_cd",
    "expected_corp_frozen_typ_cd",
    "actual_in_early_adopter",
    "expected_in_early_adopter",
    "actual_send_ar_ind",
    "expected_send_ar_ind",
]

DETAIL_FIELDNAMES = _DETAIL_BASE_FIELDNAMES + _DETAIL_CHECK_FIELDNAMES


@dataclass(frozen=True)
class VerifyColinUpdatesSettings:
    """Validated settings needed by the verifier's candidate-selection phase."""

    batches: int
    batch_size: int
    selected_checks: tuple[str, ...]
    detail_path: str
    summary_path: str
    use_migration_filter: bool
    mig_batch_ids: tuple[int, ...]
    mig_group_ids: tuple[int, ...]


@dataclass(frozen=True)
class CandidateQueries:
    """Aligned candidate count/page query strings and bound parameters."""

    base_sql: str
    count_sql: str
    page_sql: str
    params: dict[str, list[int]]
    expanding_bind_names: tuple[str, ...]

    def count_statement(self) -> TextClause:
        """Return the SQLAlchemy count statement with expanding binds attached."""
        return _build_text_statement(self.count_sql, self.expanding_bind_names)

    def page_statement(self) -> TextClause:
        """Return the SQLAlchemy page statement with expanding binds attached."""
        return _build_text_statement(self.page_sql, self.expanding_bind_names)


@dataclass(frozen=True)
class OracleCorporationState:
    """Oracle state read back for one COLIN corporation identifier."""

    colin_corp_num: str
    corp_frozen_typ_cd: str | None
    send_ar_ind: str | None
    in_early_adopter: bool


@dataclass(frozen=True)
class VerificationResult:
    """Per-candidate verification result for enabled COLIN update checks."""

    original_corp_num: str
    colin_corp_num: str
    oracle_found: bool
    freeze_success: bool | None = None
    early_adopter_success: bool | None = None
    ar_ind_is_no_success: bool | None = None
    corp_frozen_typ_cd: str | None = None
    send_ar_ind: str | None = None
    in_early_adopter: bool | None = None
    mismatch_checks: tuple[str, ...] = ()

    @property
    def success(self) -> bool:
        """Return True when all enabled checks matched the expected Oracle state."""
        return not self.mismatch_checks


@dataclass(frozen=True)
class OracleReadStatement:
    """Bound Oracle read-back SQL and bind parameters."""

    sql: str
    params: dict[str, str]

    def statement(self) -> TextClause:
        """Return the SQLAlchemy text statement."""
        return text(self.sql)


def _build_text_statement(sql: str, expanding_bind_names: tuple[str, ...]) -> TextClause:
    stmt = text(sql)
    for bind_name in expanding_bind_names:
        stmt = stmt.bindparams(bindparam(bind_name, expanding=True))
    return stmt


def parse_migration_ids(csv_val: str | None, env_var_name: str) -> list[int]:
    """Strictly parse a comma-separated migration ID env var.

    Empty tokens are ignored so values like ``"1, 2, ,3"`` are accepted, but
    every non-empty token must be a base-10 integer. Invalid tokens raise a
    ``ValueError`` that names the source environment variable.
    """
    if not csv_val:
        return []

    parsed: list[int] = []
    for raw_token in csv_val.split(","):
        token = raw_token.strip()
        if not token:
            continue
        if not token.isdecimal():
            raise ValueError(f"Invalid {env_var_name} token '{token}'")
        parsed_id = int(token)
        if parsed_id <= 0:
            raise ValueError(f"Invalid {env_var_name} token '{token}'")
        parsed.append(parsed_id)
    return parsed


def get_selected_checks(config: Any) -> tuple[str, ...]:
    """Return enabled verification checks in stable report/query order."""
    return tuple(
        check_name
        for check_name, attr_name in _CHECK_CONFIG_ATTRS.items()
        if bool(getattr(config, attr_name, False))
    )


def _coerce_int_setting(config: Any, attr_name: str) -> int:
    raw_value = getattr(config, attr_name, 0)
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{attr_name} must be a valid integer") from exc


def _resolved_output_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def validate_config(config: Any) -> VerifyColinUpdatesSettings:
    """Validate verifier config before database connections are opened."""
    batches = _coerce_int_setting(config, "VERIFY_COLIN_UPDATES_BATCHES")
    if batches <= 0:
        raise ValueError("VERIFY_COLIN_UPDATES_BATCHES must be greater than 0")

    batch_size = _coerce_int_setting(config, "VERIFY_COLIN_UPDATES_BATCH_SIZE")
    if batch_size <= 0:
        raise ValueError("VERIFY_COLIN_UPDATES_BATCH_SIZE must be greater than 0")
    if batch_size > ORACLE_IN_LIMIT:
        raise ValueError(f"VERIFY_COLIN_UPDATES_BATCH_SIZE must be between 1 and {ORACLE_IN_LIMIT}")

    selected_checks = get_selected_checks(config)
    if not selected_checks:
        raise ValueError("At least one VERIFY_COLIN_UPDATES_CHECK_* option must be enabled")

    detail_path = getattr(config, "VERIFY_COLIN_UPDATES_DETAIL_PATH", None)
    if not detail_path:
        raise ValueError("VERIFY_COLIN_UPDATES_DETAIL_PATH must be set")

    summary_path = getattr(config, "VERIFY_COLIN_UPDATES_SUMMARY_PATH", None)
    if not summary_path:
        raise ValueError("VERIFY_COLIN_UPDATES_SUMMARY_PATH must be set")
    if _resolved_output_path(str(detail_path)) == _resolved_output_path(str(summary_path)):
        raise ValueError("VERIFY_COLIN_UPDATES_DETAIL_PATH and VERIFY_COLIN_UPDATES_SUMMARY_PATH must be different")

    use_migration_filter = bool(getattr(config, "USE_MIGRATION_FILTER", False))
    mig_batch_ids: list[int] = []
    mig_group_ids: list[int] = []
    if use_migration_filter:
        mig_batch_ids = parse_migration_ids(getattr(config, "MIG_BATCH_IDS", None), "MIG_BATCH_IDS")
        mig_group_ids = parse_migration_ids(getattr(config, "MIG_GROUP_IDS", None), "MIG_GROUP_IDS")
        if not mig_batch_ids and not mig_group_ids:
            raise ValueError(
                "USE_MIGRATION_FILTER=True requires at least one valid MIG_BATCH_IDS or MIG_GROUP_IDS value"
            )

    return VerifyColinUpdatesSettings(
        batches=batches,
        batch_size=batch_size,
        selected_checks=selected_checks,
        detail_path=detail_path,
        summary_path=summary_path,
        use_migration_filter=use_migration_filter,
        mig_batch_ids=tuple(mig_batch_ids),
        mig_group_ids=tuple(mig_group_ids),
    )


def get_default_candidate_filter_fragments() -> tuple[str, str]:
    """Manual query hook for exceptional non-migration candidate narrowing.

    By default this returns no CTE and no additional predicate, so non-migration
    mode selects all rows from ``corporation c``. Developers may temporarily edit
    this helper for one-off verification scenarios instead of adding runtime
    selection environment variables.
    """
    return "", ""


def _normalize_fragment(fragment: str | None) -> str:
    return (fragment or "").strip()


def _build_base_candidate_sql(settings: VerifyColinUpdatesSettings) -> tuple[str, dict[str, list[int]], tuple[str, ...]]:
    """Build the shared base candidate relation for count and page queries."""
    params: dict[str, list[int]] = {}
    expanding_bind_names: list[str] = []

    if settings.use_migration_filter:
        filters: list[str] = []
        if settings.mig_batch_ids:
            filters.append("AND b.id IN :mig_batch_ids")
            params["mig_batch_ids"] = list(settings.mig_batch_ids)
            expanding_bind_names.append("mig_batch_ids")
        if settings.mig_group_ids:
            filters.append("AND g.id IN :mig_group_ids")
            params["mig_group_ids"] = list(settings.mig_group_ids)
            expanding_bind_names.append("mig_group_ids")

        base_sql = f"""
            SELECT DISTINCT c.corp_num
            FROM mig_corp_batch mcb
            JOIN mig_batch b ON b.id = mcb.mig_batch_id
            JOIN mig_group g ON g.id = b.mig_group_id
            JOIN corporation c ON c.corp_num = mcb.corp_num
            WHERE 1 = 1
            {' '.join(filters)}
        """
        return base_sql.strip(), params, tuple(expanding_bind_names)

    cte_clause, where_clause = get_default_candidate_filter_fragments()
    cte_clause = _normalize_fragment(cte_clause)
    where_clause = _normalize_fragment(where_clause)
    cte_prefix = f"{cte_clause}\n" if cte_clause else ""
    extra_where = f"\n            {where_clause}" if where_clause else ""

    base_sql = f"""
        {cte_prefix}SELECT c.corp_num
        FROM corporation c
        WHERE 1 = 1{extra_where}
    """
    return base_sql.strip(), params, tuple(expanding_bind_names)


def build_candidate_queries(config: Any) -> CandidateQueries:
    """Build aligned candidate count and page queries for the configured mode."""
    settings = validate_config(config)
    base_sql, params, expanding_bind_names = _build_base_candidate_sql(settings)

    count_sql = f"""
        SELECT COUNT(*)
        FROM (
            {base_sql}
        ) candidates
    """.strip()

    page_sql = f"""
        SELECT corp_num
        FROM (
            {base_sql}
        ) candidates
        ORDER BY corp_num
        LIMIT :limit OFFSET :offset
    """.strip()

    return CandidateQueries(
        base_sql=base_sql,
        count_sql=count_sql,
        page_sql=page_sql,
        params=params,
        expanding_bind_names=expanding_bind_names,
    )


def normalize_candidate_corp_nums(corp_nums: list[str]) -> list[str]:
    """Normalize extract identifiers to COLIN Oracle corp_num format."""
    return [convert_to_colin_format(str(corp_num)) for corp_num in corp_nums]


def build_oracle_read_statement(colin_corp_nums: list[str]) -> OracleReadStatement:
    """Build the bounded Oracle read-back statement for one verifier batch."""
    if len(colin_corp_nums) > ORACLE_IN_LIMIT:
        raise ValueError(f"Oracle read-back batch size {len(colin_corp_nums)} exceeds ORACLE_IN_LIMIT {ORACLE_IN_LIMIT}")
    in_clause, in_params = build_in_bind_clause(colin_corp_nums)
    return OracleReadStatement(
        sql=ORACLE_READ_BACK_QUERY.format(corp_nums=in_clause),
        params=in_params,
    )


def _mapping_value(row: Any, index: int, *names: str) -> Any:
    if hasattr(row, "_mapping"):
        mapping = row._mapping
        for name in names:
            if name in mapping:
                return mapping[name]
        lowered = {str(key).lower(): value for key, value in mapping.items()}
        for name in names:
            value = lowered.get(name.lower())
            if value is not None or name.lower() in lowered:
                return value
    return row[index]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().upper() in {"1", "Y", "YES", "TRUE", "T"}


def _oracle_row_to_state(row: Any) -> OracleCorporationState:
    return OracleCorporationState(
        colin_corp_num=str(_mapping_value(row, 0, "corp_num")),
        corp_frozen_typ_cd=_mapping_value(row, 1, "corp_frozen_typ_cd"),
        send_ar_ind=_mapping_value(row, 2, "SEND_AR_IND", "send_ar_ind"),
        in_early_adopter=_to_bool(_mapping_value(row, 3, "in_early_adopter")),
    )


def read_oracle_corp_states(colin_oracle_engine: Engine, colin_corp_nums: list[str]) -> dict[str, OracleCorporationState]:
    """Read Oracle state for normalized COLIN corp identifiers using bound IN params."""
    if not colin_corp_nums:
        return {}

    read_statement = build_oracle_read_statement(colin_corp_nums)
    with colin_oracle_engine.connect() as conn:
        rows = conn.execute(read_statement.statement(), read_statement.params).fetchall()
    states = [_oracle_row_to_state(row) for row in rows]
    return {state.colin_corp_num: state for state in states}


def _build_missing_result(original_corp_num: str, colin_corp_num: str, selected_checks: tuple[str, ...]) -> VerificationResult:
    return VerificationResult(
        original_corp_num=original_corp_num,
        colin_corp_num=colin_corp_num,
        oracle_found=False,
        freeze_success=False if CHECK_FREEZE in selected_checks else None,
        early_adopter_success=False if CHECK_EARLY_ADOPTER in selected_checks else None,
        ar_ind_is_no_success=False if CHECK_AR_IND_IS_NO in selected_checks else None,
        mismatch_checks=("oracle_missing", *selected_checks),
    )


def build_verification_results(
    original_corp_nums: list[str],
    oracle_states: dict[str, OracleCorporationState],
    selected_checks: tuple[str, ...],
) -> list[VerificationResult]:
    """Compare Oracle state to expected values for each selected candidate corp."""
    results: list[VerificationResult] = []
    normalized_corp_nums = normalize_candidate_corp_nums(original_corp_nums)

    for original_corp_num, colin_corp_num in zip(original_corp_nums, normalized_corp_nums):
        original_corp_num = str(original_corp_num)
        state = oracle_states.get(colin_corp_num)
        if state is None:
            results.append(_build_missing_result(original_corp_num, colin_corp_num, selected_checks))
            continue

        mismatch_checks: list[str] = []
        freeze_success: bool | None = None
        early_adopter_success: bool | None = None
        ar_ind_is_no_success: bool | None = None

        if CHECK_FREEZE in selected_checks:
            freeze_success = state.corp_frozen_typ_cd == EXPECTED_FREEZE_TYP_CD
            if not freeze_success:
                mismatch_checks.append(CHECK_FREEZE)

        if CHECK_EARLY_ADOPTER in selected_checks:
            early_adopter_success = state.in_early_adopter is EXPECTED_IN_EARLY_ADOPTER
            if not early_adopter_success:
                mismatch_checks.append(CHECK_EARLY_ADOPTER)

        if CHECK_AR_IND_IS_NO in selected_checks:
            ar_ind_is_no_success = state.send_ar_ind == EXPECTED_SEND_AR_IND_IS_NO
            if not ar_ind_is_no_success:
                mismatch_checks.append(CHECK_AR_IND_IS_NO)

        results.append(
            VerificationResult(
                original_corp_num=original_corp_num,
                colin_corp_num=colin_corp_num,
                oracle_found=True,
                freeze_success=freeze_success,
                early_adopter_success=early_adopter_success,
                ar_ind_is_no_success=ar_ind_is_no_success,
                corp_frozen_typ_cd=state.corp_frozen_typ_cd,
                send_ar_ind=state.send_ar_ind,
                in_early_adopter=state.in_early_adopter,
                mismatch_checks=tuple(mismatch_checks),
            )
        )

    return results


def verify_oracle_batch(config: Any, colin_oracle_engine: Engine, corp_nums: list[str]) -> list[VerificationResult]:
    """Read and verify one configured candidate batch against Oracle state."""
    settings = validate_config(config)
    if len(corp_nums) > settings.batch_size:
        raise ValueError(
            f"Verifier batch contains {len(corp_nums)} candidates, exceeding configured "
            f"VERIFY_COLIN_UPDATES_BATCH_SIZE {settings.batch_size}"
        )
    colin_corp_nums = normalize_candidate_corp_nums(corp_nums)
    oracle_states = read_oracle_corp_states(colin_oracle_engine, colin_corp_nums)
    return build_verification_results(corp_nums, oracle_states, settings.selected_checks)


def _check_success(result: VerificationResult, check_name: str) -> bool | None:
    if check_name == CHECK_FREEZE:
        return result.freeze_success
    if check_name == CHECK_EARLY_ADOPTER:
        return result.early_adopter_success
    if check_name == CHECK_AR_IND_IS_NO:
        return result.ar_ind_is_no_success
    raise ValueError(f"Unsupported check name: {check_name}")


def build_summary_row(results: list[VerificationResult], selected_checks: tuple[str, ...]) -> dict[str, int]:
    """Build a compact aggregate summary row for all verification results."""
    summary = {
        "total_count": len(results),
        "success_count": sum(1 for result in results if result.success),
        "failure_count": sum(1 for result in results if not result.success),
    }
    for check_name in selected_checks:
        values = [_check_success(result, check_name) for result in results]
        summary[f"{check_name}_success_count"] = sum(1 for value in values if value is True)
        summary[f"{check_name}_failure_count"] = sum(1 for value in values if value is False)
    return summary


def format_enabled_check_summary(summary: dict[str, int], selected_checks: tuple[str, ...]) -> str:
    """Format per-enabled-check success/failure counts for operational logging."""
    return "; ".join(
        f"{check_name}(success={summary[f'{check_name}_success_count']}, "
        f"failure={summary[f'{check_name}_failure_count']})"
        for check_name in selected_checks
    )


def _format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def build_detail_rows(results: list[VerificationResult]) -> list[dict[str, str]]:
    """Build mismatch-only detail rows for CSV output."""
    rows: list[dict[str, str]] = []
    for result in results:
        if result.success:
            continue

        row = {field_name: "" for field_name in DETAIL_FIELDNAMES}
        row.update(
            {
                "original_corp_num": result.original_corp_num,
                "colin_corp_num": result.colin_corp_num,
                "oracle_found": _format_bool(result.oracle_found),
                "mismatch_checks": ",".join(result.mismatch_checks),
            }
        )

        if CHECK_FREEZE in result.mismatch_checks:
            row["actual_corp_frozen_typ_cd"] = result.corp_frozen_typ_cd or ""
            row["expected_corp_frozen_typ_cd"] = EXPECTED_FREEZE_TYP_CD
        if CHECK_EARLY_ADOPTER in result.mismatch_checks:
            row["actual_in_early_adopter"] = _format_bool(result.in_early_adopter)
            row["expected_in_early_adopter"] = _format_bool(EXPECTED_IN_EARLY_ADOPTER)
        if CHECK_AR_IND_IS_NO in result.mismatch_checks:
            row["actual_send_ar_ind"] = result.send_ar_ind or ""
            row["expected_send_ar_ind"] = EXPECTED_SEND_AR_IND_IS_NO

        rows.append(row)
    return rows


def _ensure_parent_dir(path: str) -> Path:
    expanded_path = Path(path).expanduser()
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    return expanded_path


def write_summary_csv(path: str, results: list[VerificationResult], selected_checks: tuple[str, ...]) -> None:
    """Write the aggregate summary CSV report."""
    summary_row = build_summary_row(results, selected_checks)
    fieldnames = SUMMARY_FIELDNAMES + [
        field_name
        for check_name in selected_checks
        for field_name in (f"{check_name}_success_count", f"{check_name}_failure_count")
    ]
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(summary_row)


def write_detail_csv(path: str, results: list[VerificationResult]) -> None:
    """Write the mismatch-only detail CSV report, including headers when empty."""
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=DETAIL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(build_detail_rows(results))


def write_verification_reports(
    settings: VerifyColinUpdatesSettings,
    results: list[VerificationResult],
) -> None:
    """Write both configured verifier CSV reports."""
    write_summary_csv(settings.summary_path, results, settings.selected_checks)
    write_detail_csv(settings.detail_path, results)


def calculate_batch_count(total_candidates: int, batch_size: int, configured_batches: int) -> int:
    """Return the number of candidate pages to verify for this run."""
    if total_candidates <= 0:
        return 0
    return min(math.ceil(total_candidates / batch_size), configured_batches)


def _resolve_task_result(value: Any) -> Any:
    """Resolve Prefect futures while leaving plain test doubles untouched."""
    return value.result() if hasattr(value, "result") else value


def _submit_verify_batch(config: Any, colin_oracle_engine: Engine, corp_nums: list[str]) -> Any:
    """Submit one Oracle verification task, with a sync fallback for non-Prefect tests."""
    if hasattr(verify_oracle_batch_task, "submit"):
        return verify_oracle_batch_task.submit(config, colin_oracle_engine, corp_nums)
    return verify_oracle_batch_task(config, colin_oracle_engine, corp_nums)


@task(name="Verify COLIN update Oracle batch", cache_policy=NO_CACHE)
def verify_oracle_batch_task(config: Any, colin_oracle_engine: Engine, corp_nums: list[str]) -> list[VerificationResult]:
    """Prefect task wrapper for one Oracle read-back verification batch."""
    return verify_oracle_batch(config, colin_oracle_engine, corp_nums)


@task(name="Count verify COLIN update candidates", cache_policy=NO_CACHE)
def get_candidate_count(config: Any, colin_extract_engine: Engine) -> int:
    """Execute the aligned candidate count query."""
    queries = build_candidate_queries(config)
    with colin_extract_engine.connect() as conn:
        return int(conn.execute(queries.count_statement(), queries.params).scalar() or 0)


@task(name="Page verify COLIN update candidates", cache_policy=NO_CACHE)
def get_candidate_page(config: Any, colin_extract_engine: Engine, limit: int, offset: int) -> list[str]:
    """Execute the aligned candidate page query with deterministic ordering."""
    queries = build_candidate_queries(config)
    params: dict[str, Any] = {**queries.params, "limit": limit, "offset": offset}
    with colin_extract_engine.connect() as conn:
        rows = conn.execute(queries.page_statement(), params).fetchall()
        return [row[0] for row in rows]


@flow(name="Verify-Colin-Updates-Flow", log_prints=True)
def verify_colin_updates_flow():
    """Validate config, verify selected COLIN update candidates, and write reports."""
    config = get_config()
    settings = validate_config(config)

    print(
        "👷 Verify COLIN updates starting. "
        f"UseMigrationFilter={settings.use_migration_filter}, "
        f"SelectedChecks={','.join(settings.selected_checks)}, "
        f"ConfiguredBatches={settings.batches}, BatchSize={settings.batch_size}"
    )

    # Build once before connecting so config/query validation happens as early as practical.
    build_candidate_queries(config)

    colin_extract_engine = colin_extract_init(config)
    colin_oracle_engine = colin_oracle_init(config)

    total_candidates = get_candidate_count(config, colin_extract_engine)
    total_candidates = int(_resolve_task_result(total_candidates) or 0)
    batch_count = calculate_batch_count(total_candidates, settings.batch_size, settings.batches)
    print(
        "👷 Candidate selection ready. "
        f"TotalCandidates={total_candidates}, BatchCount={batch_count}, "
        f"UseMigrationFilter={settings.use_migration_filter}, "
        f"MigGroupIds={settings.mig_group_ids or '(none)'}, "
        f"MigBatchIds={settings.mig_batch_ids or '(none)'}"
    )

    futures: list[Any] = []
    for batch_index in range(batch_count):
        offset = batch_index * settings.batch_size
        corp_nums = get_candidate_page(config, colin_extract_engine, settings.batch_size, offset)
        corp_nums = list(_resolve_task_result(corp_nums) or [])
        print(
            f"🚀 Submitting verify batch {batch_index + 1}/{batch_count}: "
            f"offset={offset}, candidate_count={len(corp_nums)}"
        )
        futures.append(_submit_verify_batch(config, colin_oracle_engine, corp_nums))

    results: list[VerificationResult] = []
    for future in futures:
        batch_results = _resolve_task_result(future) or []
        results.extend(batch_results)

    summary = build_summary_row(results, settings.selected_checks)
    mismatch_count = len(build_detail_rows(results))
    enabled_check_summary = format_enabled_check_summary(summary, settings.selected_checks)
    print(
        "🌟 Verification tasks complete. "
        f"TotalVerified={summary['total_count']}, Success={summary['success_count']}, "
        f"Failure={summary['failure_count']}, MismatchRows={mismatch_count}, "
        f"EnabledCheckSummary={enabled_check_summary}"
    )

    write_verification_reports(settings, results)
    print(
        "🌰 Verify COLIN updates reports written. "
        f"SummaryPath={settings.summary_path}, DetailPath={settings.detail_path}"
    )

    return summary


if __name__ == "__main__":
    verify_colin_updates_flow()
