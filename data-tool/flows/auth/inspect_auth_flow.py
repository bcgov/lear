"""Read-only Prefect inspection flow for Auth DB state.

This module provides the dedicated inspect-auth entrypoint. It shares the
verify-auth candidate selection, expected-account lookup, Auth DB read-back,
inspection row builders, CSV writer, Prefect fallback decorators, and console
limit helpers while using shared AUTH_REPORT_* throughput plus inspect-specific
INSPECT_AUTH_* configuration, including expression-based INSPECT_AUTH_INVITE_CRITERIA
and defaulted diagnostics-only INSPECT_AUTH_INVITE_EXPIRY_DAYS.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.engine import Engine

from auth.auth_models import AuthSelectionMode
from auth.auth_selection import parse_auth_corp_nums_csv
from auth.auth_report_helpers import (
    CHECK_AFFILIATION,
    CHECK_CONTACT,
    CHECK_ENTITY,
    CHECK_INVITE,
    AUTH_OUTPUT_PATH_ATTR,
    INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA,
    AuthBatchResult,
    ConsoleLimit,
    InviteCriteria,
    blank_to_none,
    dispose_engine,
    format_clock_minutes_z,
    format_clock_z,
    format_console_limit,
    format_invite_criteria,
    is_csv_like_output_root,
    parse_auth_selection_mode,
    parse_manual_account_ids,
    parse_positive_int_tuple,
    resolve_task_result,
    build_candidate_queries,
    build_inspection_identifier_rows,
    build_inspection_rows,
    build_inspection_summary,
    calculate_batch_count,
    filter_inspection_states,
    flow,
    get_candidate_count,
    get_candidate_page,
    parse_console_limit,
    parse_inspect_filter,
    parse_invite_criteria,
    parse_invite_expiry_days,
    print_inspection_identifier_rows,
    print_inspection_rows,
    print_inspection_summary,
    read_expected_accounts_for_candidates,
    run_auth_batch,
    task,
    write_inspection_report,
    write_inspection_summary_txt,
    NO_CACHE,
)

LOGGER = logging.getLogger(__name__)

FLOW_NAME = "inspect-auth-flow"
LOCAL_THREADED_EXECUTION_ASSUMPTION = (
    "Inspect Auth assumes local/threaded Prefect execution because SQLAlchemy engine objects "
    "are shared with submitted read-only tasks; do not use distributed/process task runners."
)

DEFAULT_INSPECT_AUTH_CONSOLE_LIMIT = 25
INSPECTION_FILENAME = "inspect-auth-inspection.csv"
INSPECTION_SUMMARY_FILENAME = "inspect-auth-summary.txt"
INSPECT_AUTH_CONSOLE_LIMIT_ATTR = "INSPECT_AUTH_CONSOLE_LIMIT"
INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH_ATTR = "INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH"
INSPECT_AUTH_READ_CHECKS = (CHECK_ENTITY, CHECK_CONTACT, CHECK_AFFILIATION, CHECK_INVITE)


@dataclass(frozen=True)
class InspectAuthSettings:
    """Validated inspect-only settings needed by the inspect-auth flow."""

    batches: int
    batch_size: int
    inspect_filter: str
    console_limit: ConsoleLimit
    business_names_max_length: int | None
    inspection_path: str
    summary_path: str
    selection_mode: AuthSelectionMode
    auth_corp_nums: tuple[str, ...]
    auth_mig_group_ids: tuple[int, ...]
    auth_mig_batch_ids: tuple[int, ...]
    manual_account_ids: tuple[str, ...]
    selected_checks: tuple[str, ...] = ()
    run_clock: datetime | None = None
    invite_expiry_days: int = 7
    invite_expiry_cutoff: datetime | None = None
    invite_criteria: InviteCriteria | None = None

    @property
    def run_verify(self) -> bool:
        """Return False so shared Auth batches only read Auth state."""
        return False

    @property
    def auth_read_checks(self) -> tuple[str, ...]:
        """Return the full Auth table read scope for inspection."""
        return INSPECT_AUTH_READ_CHECKS

    @property
    def read_expected_accounts(self) -> bool:
        """Return True when expected account IDs should be included in inspect rows."""
        return self.selection_mode != AuthSelectionMode.MANUAL or bool(self.manual_account_ids)

    @property
    def invite_cutoff(self) -> datetime | None:
        """Return the once-per-run expiry cutoff used by every Auth batch."""
        return self.invite_expiry_cutoff


def _coerce_int_setting(config: Any, attr_name: str) -> int:
    raw_value = getattr(config, attr_name, 0)
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{attr_name} must be a valid integer") from exc


def parse_business_names_max_length(
    raw_value: Any,
    config_key: str = INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH_ATTR,
) -> int | None:
    """Parse the optional inspect-auth console cap for the business-names cell."""
    raw = blank_to_none(raw_value)
    if raw is None or raw.upper() == "ALL":
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{config_key} must be a positive integer or ALL") from exc
    if parsed <= 0:
        raise ValueError(f"{config_key} must be a positive integer or ALL")
    return parsed


def _derive_inspection_path(output_root: str) -> str:
    return str(Path(output_root).expanduser() / INSPECTION_FILENAME)


def _derive_summary_path(output_root: str) -> str:
    return str(Path(output_root).expanduser() / INSPECTION_SUMMARY_FILENAME)


def _resolve_inspection_paths(config: Any) -> tuple[str, str]:
    output_root = blank_to_none(getattr(config, AUTH_OUTPUT_PATH_ATTR, None))
    if not output_root:
        raise ValueError(f"{AUTH_OUTPUT_PATH_ATTR} must be set")
    if is_csv_like_output_root(output_root):
        raise ValueError(f"{AUTH_OUTPUT_PATH_ATTR} must be a directory/root path, not a .csv file path")
    return _derive_inspection_path(output_root), _derive_summary_path(output_root)


def _standalone_invite_cutoff(now_utc: datetime, expiry_days: int) -> datetime:
    """Compute a diagnostics-only cutoff with a fail-fast configuration error."""
    try:
        return now_utc - timedelta(days=expiry_days)
    except OverflowError as exc:
        raise ValueError(
            "INSPECT_AUTH_INVITE_EXPIRY_DAYS is outside the supported range for the current reference clock"
        ) from exc


def validate_inspect_config(config: Any) -> InspectAuthSettings:
    """Validate inspect-auth config before database connections are opened."""
    batches = _coerce_int_setting(config, "AUTH_REPORT_BATCHES")
    if batches <= 0:
        raise ValueError("AUTH_REPORT_BATCHES must be greater than 0")

    batch_size = _coerce_int_setting(config, "AUTH_REPORT_BATCH_SIZE")
    if batch_size <= 0:
        raise ValueError("AUTH_REPORT_BATCH_SIZE must be greater than 0")

    inspect_filter = parse_inspect_filter(getattr(config, "INSPECT_AUTH_FILTER", None), "INSPECT_AUTH_FILTER")
    invite_expiry_days = parse_invite_expiry_days(
        getattr(config, "INSPECT_AUTH_INVITE_EXPIRY_DAYS", None)
    )
    raw_invite_criteria = blank_to_none(getattr(config, "INSPECT_AUTH_INVITE_CRITERIA", None))
    if (
        raw_invite_criteria is not None
        and inspect_filter != INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA
    ):
        raise ValueError(
            "INSPECT_AUTH_INVITE_CRITERIA only applies to "
            "NO_AFFILIATION_INVITE_CRITERIA"
        )

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    invite_criteria = parse_invite_criteria(
        raw_invite_criteria,
        now=now_utc,
        expiry_days=invite_expiry_days,
    )
    if (
        inspect_filter == INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA
        and invite_criteria is None
    ):
        raise ValueError(
            "INSPECT_AUTH_INVITE_CRITERIA must contain at least one clause when "
            "INSPECT_AUTH_FILTER=NO_AFFILIATION_INVITE_CRITERIA"
        )

    invite_expiry_cutoff = (
        invite_criteria.cutoff
        if invite_criteria is not None
        else _standalone_invite_cutoff(now_utc, invite_expiry_days)
    )

    console_limit = parse_console_limit(
        getattr(config, INSPECT_AUTH_CONSOLE_LIMIT_ATTR, None),
        INSPECT_AUTH_CONSOLE_LIMIT_ATTR,
        DEFAULT_INSPECT_AUTH_CONSOLE_LIMIT,
    )
    business_names_max_length = parse_business_names_max_length(
        getattr(config, INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH_ATTR, None)
    )
    inspection_path, summary_path = _resolve_inspection_paths(config)

    selection_mode = parse_auth_selection_mode(config)
    auth_corp_nums = tuple(parse_auth_corp_nums_csv(getattr(config, "AUTH_CORP_NUMS", None)))

    auth_mig_group_ids: tuple[int, ...] = ()
    auth_mig_batch_ids: tuple[int, ...] = ()
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        auth_mig_group_ids = parse_positive_int_tuple(config, "AUTH_MIG_GROUP_IDS")
        auth_mig_batch_ids = parse_positive_int_tuple(config, "AUTH_MIG_BATCH_IDS")
        if not (auth_mig_group_ids or auth_mig_batch_ids):
            raise ValueError(
                "AUTH_SELECTION_MODE=MIGRATION_FILTER requires AUTH_MIG_GROUP_IDS and/or AUTH_MIG_BATCH_IDS; "
                "Auth inspection does not fall back to global MIG_GROUP_IDS/MIG_BATCH_IDS"
            )

    manual_account_ids: tuple[str, ...] = ()
    if selection_mode == AuthSelectionMode.MANUAL:
        manual_account_ids = parse_manual_account_ids(config)

    return InspectAuthSettings(
        batches=batches,
        batch_size=batch_size,
        inspect_filter=inspect_filter,
        console_limit=console_limit,
        business_names_max_length=business_names_max_length,
        inspection_path=inspection_path,
        summary_path=summary_path,
        selection_mode=selection_mode,
        auth_corp_nums=auth_corp_nums,
        auth_mig_group_ids=auth_mig_group_ids,
        auth_mig_batch_ids=auth_mig_batch_ids,
        manual_account_ids=manual_account_ids,
        run_clock=now_utc,
        invite_expiry_days=invite_expiry_days,
        invite_expiry_cutoff=invite_expiry_cutoff,
        invite_criteria=invite_criteria,
    )


@task(name="Count inspect Auth candidates", cache_policy=NO_CACHE)
def get_inspect_candidate_count_task(
    config: Any,
    colin_extract_engine: Engine,
    settings: InspectAuthSettings,
) -> int:
    """Prefect task wrapper for inspect selected-candidate counting."""
    return get_candidate_count(config, colin_extract_engine, settings)


@task(name="Page inspect Auth candidates", cache_policy=NO_CACHE)
def get_inspect_candidate_page_task(
    config: Any,
    colin_extract_engine: Engine,
    limit: int,
    offset: int,
    settings: InspectAuthSettings,
) -> list[str]:
    """Prefect task wrapper for deterministic inspect candidate paging."""
    return get_candidate_page(config, colin_extract_engine, limit, offset, settings)


@task(name="Read inspect Auth expected affiliation accounts", cache_policy=NO_CACHE)
def read_inspect_expected_accounts_task(
    config: Any,
    colin_extract_engine: Engine,
    business_identifiers: list[str],
    settings: InspectAuthSettings,
) -> dict[str, tuple[str, ...]]:
    """Prefect task wrapper for read-only expected-account derivation."""
    return read_expected_accounts_for_candidates(config, colin_extract_engine, business_identifiers, settings)


@task(name="Inspect Auth DB batch", cache_policy=NO_CACHE)
def inspect_auth_batch_task(
    config: Any,
    auth_engine: Engine,
    business_identifiers: list[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None,
    settings: InspectAuthSettings,
) -> AuthBatchResult:
    """Prefect task wrapper for one inspect Auth DB read-back batch."""
    return run_auth_batch(config, auth_engine, business_identifiers, expected_accounts_by_identifier, settings)


def _submit_inspect_batch(
    config: Any,
    auth_engine: Engine,
    business_identifiers: list[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None,
    settings: InspectAuthSettings,
) -> Any:
    """Submit one Auth inspection task, with a sync fallback for non-Prefect tests."""
    args = (config, auth_engine, business_identifiers, expected_accounts_by_identifier, settings)
    if hasattr(inspect_auth_batch_task, "submit"):
        return inspect_auth_batch_task.submit(*args)
    return inspect_auth_batch_task(*args)


def _format_start_message(settings: InspectAuthSettings) -> str:
    criteria_fragment = ""
    if settings.invite_criteria is not None:
        criteria_fragment = (
            f"{format_invite_criteria(settings.invite_criteria)}, "
            "CriteriaRole=filter, "
            "AgeRule=timestamp-precision vs Now; "
            "PositionRule=1=oldest, ties by (sent_date, entity_id, id); "
            "NULL sent_date fails age clauses and all_expired; "
        )
    cutoff_text = format_clock_z(settings.invite_cutoff)
    expiry_role = (
        "filter-clause"
        if settings.invite_criteria is not None and settings.invite_criteria.requires_expiry()
        else "diagnostics-only"
    )
    expiry_parameters = (
        ""
        if settings.invite_criteria is not None
        else f"ExpiryDays={settings.invite_expiry_days}, Cutoff={cutoff_text}, "
    )
    expiry_fragment = (
        f"{expiry_parameters}ExpiryRole={expiry_role}, "
        "CutoffClock=UTC once-per-run, "
    )
    return (
        "👷 Inspect Auth starting. "
        f"SelectionMode={settings.selection_mode.value}, "
        f"InspectFilter={settings.inspect_filter}, "
        f"{criteria_fragment}"
        f"{expiry_fragment}"
        f"AuthReadChecks={','.join(settings.auth_read_checks)}, "
        f"ConsoleLimit={format_console_limit(settings.console_limit)}, "
        f"ConfiguredBatches={settings.batches}, BatchSize={settings.batch_size}, "
        "RunnerAssumption=local/threaded"
    )


def _resolve_inspect_batch_states(futures: list[Any]) -> list[Any]:
    """Resolve submitted inspect batches into one ordered state list."""
    states = []
    for future in futures:
        batch_result = resolve_task_result(future)
        if isinstance(batch_result, AuthBatchResult):
            states.extend(batch_result.states)
        else:
            # Compatibility for simple task doubles that return raw AuthBusinessState lists.
            states.extend(batch_result or [])
    return states


def _run_inspect_auth_flow_with_engines(
    config: Any,
    settings: InspectAuthSettings,
    colin_extract_engine: Engine,
    auth_engine: Engine,
) -> dict[str, Any]:
    """Run inspect-auth orchestration using already-initialized engines."""
    total_candidates = get_inspect_candidate_count_task(config, colin_extract_engine, settings)
    total_candidates = int(resolve_task_result(total_candidates) or 0)
    batch_count = calculate_batch_count(total_candidates, settings.batch_size, settings.batches)
    print(
        "👷 Auth candidate selection ready. "
        f"TotalCandidates={total_candidates}, BatchCount={batch_count}, "
        f"SelectionMode={settings.selection_mode.value}, "
        f"AuthMigGroupIds={settings.auth_mig_group_ids or '(none)'}, "
        f"AuthMigBatchIds={settings.auth_mig_batch_ids or '(none)'}, "
        f"InspectFilter={settings.inspect_filter}"
    )

    futures: list[Any] = []
    for batch_index in range(batch_count):
        offset = batch_index * settings.batch_size
        business_identifiers = get_inspect_candidate_page_task(
            config,
            colin_extract_engine,
            settings.batch_size,
            offset,
            settings,
        )
        business_identifiers = [str(identifier) for identifier in (resolve_task_result(business_identifiers) or [])]

        expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None
        if settings.read_expected_accounts:
            expected_accounts_by_identifier = read_inspect_expected_accounts_task(
                config,
                colin_extract_engine,
                business_identifiers,
                settings,
            )
            expected_accounts_by_identifier = resolve_task_result(expected_accounts_by_identifier) or {}

        print(
            f"🚀 Submitting inspect-auth batch {batch_index + 1}/{batch_count}: "
            f"offset={offset}, candidate_count={len(business_identifiers)}"
        )
        futures.append(
            _submit_inspect_batch(
                config,
                auth_engine,
                business_identifiers,
                expected_accounts_by_identifier,
                settings,
            )
        )

    states = _resolve_inspect_batch_states(futures)

    matched_states = filter_inspection_states(
        states, settings.inspect_filter, settings.invite_criteria
    )
    inspection_rows = build_inspection_rows(
        matched_states,
        settings.invite_criteria,
        reference_now=settings.run_clock,
    )
    identifier_rows = build_inspection_identifier_rows(
        states, matched_states, settings.inspect_filter, settings.invite_criteria
    )
    summary = build_inspection_summary(
        states, matched_states, settings.inspect_filter, settings.invite_criteria
    )
    summary["expiry_days"] = settings.invite_expiry_days
    summary["expiry_cutoff"] = settings.invite_cutoff

    print(
        "🌟 Inspect Auth tasks complete. "
        f"TotalInspected={summary['inspected_count']}, Matched={summary['matched_count']}, "
        f"IdentifierGroups={len(identifier_rows)}"
    )
    print_inspection_summary(
        states, matched_states, settings.inspect_filter, settings.invite_criteria
    )
    run_clock_text = format_clock_minutes_z(settings.run_clock)
    invite_cutoff_text = format_clock_minutes_z(settings.invite_cutoff)
    print(
        "🕐 Invite clock: "
        f"Now={run_clock_text}  Cutoff={invite_cutoff_text}  "
        f"ExpiryDays={settings.invite_expiry_days}  "
        "(expired means sent_date < Cutoff; one clock per run)"
    )
    print_inspection_rows(
        inspection_rows,
        console_limit=settings.console_limit,
        report_path=settings.inspection_path,
        limit_config_key=INSPECT_AUTH_CONSOLE_LIMIT_ATTR,
        business_names_max_length=settings.business_names_max_length,
    )
    print_inspection_identifier_rows(
        identifier_rows,
        settings.inspect_filter,
        console_limit=settings.console_limit,
        copy_list_path=settings.summary_path,
        limit_config_key=INSPECT_AUTH_CONSOLE_LIMIT_ATTR,
    )

    write_inspection_report(
        settings.inspection_path,
        matched_states,
        settings.invite_criteria,
        reference_now=settings.run_clock,
    )
    write_inspection_summary_txt(
        settings.summary_path,
        identifier_rows,
        summary,
        handoff_filter=settings.inspect_filter,
    )
    if (
        settings.inspect_filter == INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA
        and identifier_rows
        and int(identifier_rows[0].get("count", 0) or 0) > 0
    ):
        print(
            f"➡️  Reminder handoff block written to {settings.summary_path} — "
            "set a new AUTH_REPEATABLE_CYCLE_KEY before running make run-auth-invite."
        )
    print(
        "🌰 Inspect Auth reports written. "
        f"InspectionPath={settings.inspection_path}, SummaryPath={settings.summary_path}"
    )

    return summary


def _initialize_and_run_inspect_auth_flow() -> dict[str, Any]:
    """Validate config, initialize engines once, and run inspect-auth orchestration."""
    from common.init_utils import auth_init, colin_extract_init, get_config

    config = get_config()
    settings = validate_inspect_config(config)
    print(_format_start_message(settings))
    LOGGER.info(LOCAL_THREADED_EXECUTION_ASSUMPTION)

    # Build once before connecting so config/query validation happens early. INSPECT_AUTH_FILTER
    # is intentionally not involved in candidate SQL; it is applied after Auth read-back.
    build_candidate_queries(config, settings)

    colin_extract_engine = colin_extract_init(config)
    auth_engine = None
    try:
        auth_engine = auth_init(config)
        return _run_inspect_auth_flow_with_engines(config, settings, colin_extract_engine, auth_engine)
    finally:
        dispose_engine(auth_engine)
        dispose_engine(colin_extract_engine)


@flow(name="Inspect-Auth-Flow", log_prints=True)
def inspect_auth_flow() -> dict[str, Any]:
    """Validate config, inspect selected Auth DB candidates, and write report."""
    return _initialize_and_run_inspect_auth_flow()


if __name__ == "__main__":
    inspect_auth_flow()
