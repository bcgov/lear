"""Read-only Prefect verifier flow for Auth DB state.

This module implements verify-auth configuration validation, COLIN extract
candidate selection, expected-account derivation, Auth DB read-back,
operational bucket classification, CSV report generation, and Prefect
orchestration. It performs no Auth API calls, Auth DB writes, or
auth_processing reservations.

Runtime note: this flow passes SQLAlchemy engine objects into submitted Prefect
tasks and is intended for local/threaded Prefect execution, not distributed or
process-based task runners.
"""

from __future__ import annotations

import csv
import inspect
import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.elements import TextClause

from auth.auth_models import AuthSelectionMode
from auth.auth_queries import get_auth_selected_corp_nums_query
from auth.auth_selection import parse_auth_corp_nums_csv, parse_positive_int_csv

try:  # pragma: no cover - exercised when Prefect is installed in runtime environments.
    from prefect import flow, task
    from prefect.cache_policies import NO_CACHE
except ModuleNotFoundError:  # pragma: no cover - keeps local helper import/smoke checks lightweight.
    NO_CACHE = None

    class _TaskFallback:
        def __init__(self, fn):
            self.fn = fn
            self.__name__ = getattr(fn, "__name__", "task_fallback")
            self.__doc__ = getattr(fn, "__doc__", None)

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

        def submit(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    def task(*_args, **_kwargs):
        def decorator(fn):
            return _TaskFallback(fn)

        return decorator

    def flow(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator

LOGGER = logging.getLogger(__name__)

FLOW_NAME = "verify-auth-flow"
LOCAL_THREADED_EXECUTION_ASSUMPTION = (
    "Verify Auth assumes local/threaded Prefect execution because SQLAlchemy engine objects "
    "are shared with submitted read-only tasks; do not use distributed/process task runners."
)
AFFILIATION_INVITE_WARNING = (
    "VERIFY_AUTH_CHECK_AFFILIATION and VERIFY_AUTH_CHECK_INVITE are both enabled; "
    "verification allows this historical/presence audit combination, but normal Auth create-flow "
    "side effects treat affiliation and unaffiliated invite as mutually exclusive."
)

CHECK_ENTITY = "entity"
CHECK_CONTACT = "contact"
CHECK_AFFILIATION = "affiliation"
CHECK_INVITE = "invite"

INSPECT_FILTER_ALL = "ALL"
INSPECT_FILTER_HAS_ANY_AUTH = "HAS_ANY_AUTH"
INSPECT_FILTER_HAS_ENTITY = "HAS_ENTITY"
INSPECT_FILTER_MISSING_ENTITY = "MISSING_ENTITY"
INSPECT_FILTER_HAS_CONTACT = "HAS_CONTACT"
INSPECT_FILTER_ENTITY_WITHOUT_CONTACT = "ENTITY_WITHOUT_CONTACT"
# Inspect "contact" filters intentionally mean usable contact with a non-blank email,
# not merely any Auth contact row. Raw contact row count remains available as contact_count.
INSPECT_FILTER_HAS_AFFILIATION = "HAS_AFFILIATION"
INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION = "ENTITY_WITHOUT_AFFILIATION"
INSPECT_FILTER_HAS_INVITE = "HAS_INVITE"
INSPECT_FILTER_ENTITY_WITHOUT_INVITE = "ENTITY_WITHOUT_INVITE"
INSPECT_FILTERS = (
    INSPECT_FILTER_ALL,
    INSPECT_FILTER_HAS_ANY_AUTH,
    INSPECT_FILTER_HAS_ENTITY,
    INSPECT_FILTER_MISSING_ENTITY,
    INSPECT_FILTER_HAS_CONTACT,
    INSPECT_FILTER_ENTITY_WITHOUT_CONTACT,
    INSPECT_FILTER_HAS_AFFILIATION,
    INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION,
    INSPECT_FILTER_HAS_INVITE,
    INSPECT_FILTER_ENTITY_WITHOUT_INVITE,
)
INSPECT_IDENTIFIER_FILTERS = tuple(
    inspect_filter for inspect_filter in INSPECT_FILTERS if inspect_filter != INSPECT_FILTER_ALL
)

_CHECK_CONFIG_ATTRS = {
    CHECK_ENTITY: "VERIFY_AUTH_CHECK_ENTITY",
    CHECK_CONTACT: "VERIFY_AUTH_CHECK_CONTACT",
    CHECK_AFFILIATION: "VERIFY_AUTH_CHECK_AFFILIATION",
    CHECK_INVITE: "VERIFY_AUTH_CHECK_INVITE",
}

AUTH_OUTPUT_PATH_ATTR = "AUTH_OUTPUT_PATH"
SUMMARY_PATH_KEY = "summary_path"
DETAIL_PATH_KEY = "detail_path"
SCENARIO_PATH_KEY = "scenario_path"

_DERIVED_OUTPUT_FILENAMES = {
    SUMMARY_PATH_KEY: "verify-auth-summary.csv",
    DETAIL_PATH_KEY: "verify-auth-detail.csv",
    SCENARIO_PATH_KEY: "verify-auth-scenario.txt",
}


DEFAULT_VERIFY_AUTH_CONSOLE_LIMIT = 25
ANSI_BOLD_RED = "\033[1;31m"
ANSI_RESET = "\033[0m"
IDENTIFIER_GROUP_SEPARATOR = "─" * 88

_DEPENDENT_CHECKS = (CHECK_CONTACT, CHECK_AFFILIATION, CHECK_INVITE)
_ALL_CHECKS = (CHECK_ENTITY, CHECK_CONTACT, CHECK_AFFILIATION, CHECK_INVITE)

SCENARIO_MISSING_ANY = "missing_any"
SCENARIO_MISSING_ALL_AUTH_INFO = "missing_all_auth_info"
SCENARIO_CONTACT_MISSING = "contact_missing"
SCENARIO_AFFILIATION_MISSING = "affiliation_missing"
SCENARIO_INVITE_MISSING = "invite_missing"
SCENARIO_AFFILIATION_NO_EXPECTED = "affiliation_no_expected_accounts"

SCENARIO_RECOMMENDED_ACTIONS = {
    SCENARIO_MISSING_ANY: "Source list for broad follow-up.",
    SCENARIO_MISSING_ALL_AUTH_INFO: "Run auth create flow.",
    SCENARIO_CONTACT_MISSING: "Run auth contact flow.",
    SCENARIO_AFFILIATION_MISSING: "Run auth affiliation flow.",
    SCENARIO_INVITE_MISSING: "Run auth invite flow.",
    SCENARIO_AFFILIATION_NO_EXPECTED: "Fix targeting/account config before backfill.",
}

SCENARIO_ORDER = tuple(SCENARIO_RECOMMENDED_ACTIONS)

_SUMMARY_BASE_FIELDNAMES = [
    "total_count",
    "success_count",
    "failure_count",
    "missing_any_count",
]

DETAIL_FIELDNAMES = [
    "business_identifier",
    "missing_elements",
    "missing_reasons",
    "scenario_buckets",
    "blocked_by_missing_entity",
    "entity_exists",
    "entity_success",
    "contact_success",
    "affiliation_success",
    "invite_success",
    "entity_ids",
    "contact_count",
    "usable_contact_count",
    "expected_account_ids",
    "found_account_ids",
    "missing_account_ids",
    "invite_count",
]

INSPECTION_FIELDNAMES = [
    "business_identifier",
    "business_names",
    "entity_state",
    "entity_exists",
    "entity_count",
    "entity_ids",
    "contact_state",
    "contact_count",
    "usable_contact_count",
    "affiliation_state",
    "affiliation_count",
    "found_account_ids",
    "found_account_names",
    "expected_account_ids",
    "missing_account_ids",
    "invite_state",
    "invite_count",
    "blocked_by_missing_entity",
]

_ENTITY_READ_SQL = """
    SELECT id, business_identifier, name AS business_name
    FROM entities
    WHERE business_identifier IN :business_identifiers
    ORDER BY business_identifier, id
""".strip()

_CONTACT_READ_SQL = """
    SELECT cl.entity_id, c.id AS contact_id, c.email
    FROM contact_links cl
    JOIN contacts c ON c.id = cl.contact_id
    WHERE cl.entity_id IN :entity_ids
    ORDER BY cl.entity_id, c.id
""".strip()

_AFFILIATION_READ_SQL = """
    SELECT a.entity_id, a.org_id, o.name AS org_name
    FROM affiliations a
    LEFT JOIN orgs o ON o.id = a.org_id
    WHERE a.entity_id IN :entity_ids
    ORDER BY a.entity_id, a.org_id
""".strip()

_INVITE_READ_SQL = """
    SELECT entity_id, COUNT(*) AS invite_count
    FROM affiliation_invitations
    WHERE entity_id IN :entity_ids
    GROUP BY entity_id
""".strip()


class AuthBatchSettings(Protocol):
    """Structural settings surface consumed by the shared Auth batch reader."""

    batch_size: int
    selected_checks: tuple[str, ...]

    @property
    def run_verify(self) -> bool:
        """Return True when verification classifications should be built."""
        ...

    @property
    def auth_read_checks(self) -> tuple[str, ...]:
        """Return Auth DB table read scope for this batch."""
        ...


class AuthCandidateSettings(Protocol):
    """Structural settings surface consumed by shared candidate/account helpers."""

    selection_mode: AuthSelectionMode
    auth_corp_nums: tuple[str, ...]
    auth_mig_group_ids: tuple[int, ...]
    auth_mig_batch_ids: tuple[int, ...]
    manual_account_ids: tuple[str, ...]


@dataclass(frozen=True)
class ConsoleLimit:
    """Console output detail limit.

    ``disabled=True`` represents ``0`` and suppresses optional detail/identifier
    console sections. ``max_rows=None`` represents ``ALL``. Positive
    ``max_rows`` values cap preview-style console output; for verify scenario
    identifiers, the cap is applied per scenario bucket while CSV output remains
    complete.
    """

    disabled: bool = False
    max_rows: int | None = DEFAULT_VERIFY_AUTH_CONSOLE_LIMIT


@dataclass(frozen=True)
class VerifyAuthSettings:
    """Validated verify-only settings needed by the verify-auth flow."""

    batches: int
    batch_size: int
    selected_checks: tuple[str, ...]
    console_limit: ConsoleLimit
    summary_path: str | None
    detail_path: str | None
    scenario_path: str | None
    selection_mode: AuthSelectionMode
    auth_corp_nums: tuple[str, ...]
    auth_mig_group_ids: tuple[int, ...]
    auth_mig_batch_ids: tuple[int, ...]
    manual_account_ids: tuple[str, ...]

    @property
    def run_verify(self) -> bool:
        """Return True for the verify-only flow."""
        return True

    @property
    def check_affiliation(self) -> bool:
        """Return True when expected-account affiliation verification is enabled."""
        return CHECK_AFFILIATION in self.selected_checks

    @property
    def read_expected_accounts(self) -> bool:
        """Return True when expected account IDs should be derived for this run."""
        return self.check_affiliation

    @property
    def auth_read_checks(self) -> tuple[str, ...]:
        """Return Auth DB table read scope for verification."""
        return self.selected_checks


@dataclass(frozen=True)
class AuthBatchResult:
    """One batch of raw Auth state plus optional verification classifications."""

    states: list[AuthBusinessState]
    verification_results: list[VerificationResult]


@dataclass(frozen=True)
class CandidateQueries:
    """Aligned selected-candidate count/page query strings."""

    base_sql: str
    count_sql: str
    page_sql: str

    def count_statement(self) -> TextClause:
        """Return the SQLAlchemy count statement."""
        return text(self.count_sql)

    def page_statement(self) -> TextClause:
        """Return the SQLAlchemy page statement."""
        return text(self.page_sql)


@dataclass(frozen=True)
class ExpectedAccountsQuery:
    """COLIN-extract query for expected Auth affiliation accounts."""

    sql: str
    params: dict[str, Any]
    expanding_bind_names: tuple[str, ...]

    def statement(self) -> TextClause:
        """Return the SQLAlchemy statement with expanding bind parameters."""
        stmt = text(self.sql)
        for bind_name in self.expanding_bind_names:
            stmt = stmt.bindparams(bindparam(bind_name, expanding=True))
        return stmt


@dataclass(frozen=True)
class AuthReadStatement:
    """Bound Auth DB read-back SQL and bind parameters."""

    sql: str
    params: dict[str, Any]
    expanding_bind_names: tuple[str, ...]

    def statement(self) -> TextClause:
        """Return the SQLAlchemy statement with expanding bind parameters."""
        return _build_text_statement(self.sql, self.expanding_bind_names)


@dataclass(frozen=True)
class AuthBusinessState:
    """Aggregated Auth DB state for one selected business identifier."""

    business_identifier: str
    entity_ids: tuple[str, ...] = ()
    contact_count: int = 0
    usable_contact_count: int = 0
    expected_account_ids: tuple[str, ...] = ()
    found_account_ids: tuple[str, ...] = ()
    found_account_names: tuple[str, ...] = ()
    missing_account_ids: tuple[str, ...] = ()
    invite_count: int = 0
    business_names: tuple[str, ...] = ()

    @property
    def entity_exists(self) -> bool:
        """Return True when Auth has at least one exact entity identifier match."""
        return bool(self.entity_ids)


def auth_state_has_any_auth(state: AuthBusinessState) -> bool:
    """Return True when any inspected Auth component is present for a business.

    Contact presence means a usable contact with a non-blank email; raw contact
    row presence remains visible separately through ``contact_count``.
    """
    return (
        state.entity_exists
        or state.usable_contact_count > 0
        or bool(state.found_account_ids)
        or state.invite_count > 0
    )


def auth_state_matches_inspect_filter(state: AuthBusinessState, inspect_filter: str) -> bool:
    """Evaluate one AuthBusinessState against a validated inspect filter.

    ``HAS_CONTACT`` and ``ENTITY_WITHOUT_CONTACT`` intentionally use
    ``usable_contact_count`` (non-blank email), not raw ``contact_count``.
    """
    if inspect_filter == INSPECT_FILTER_ALL:
        return True
    if inspect_filter == INSPECT_FILTER_HAS_ANY_AUTH:
        return auth_state_has_any_auth(state)
    if inspect_filter == INSPECT_FILTER_HAS_ENTITY:
        return state.entity_exists
    if inspect_filter == INSPECT_FILTER_MISSING_ENTITY:
        return not state.entity_exists
    if inspect_filter == INSPECT_FILTER_HAS_CONTACT:
        return state.entity_exists and state.usable_contact_count > 0
    if inspect_filter == INSPECT_FILTER_ENTITY_WITHOUT_CONTACT:
        return state.entity_exists and state.usable_contact_count == 0
    if inspect_filter == INSPECT_FILTER_HAS_AFFILIATION:
        return state.entity_exists and bool(state.found_account_ids)
    if inspect_filter == INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION:
        return state.entity_exists and not state.found_account_ids
    if inspect_filter == INSPECT_FILTER_HAS_INVITE:
        return state.entity_exists and state.invite_count > 0
    if inspect_filter == INSPECT_FILTER_ENTITY_WITHOUT_INVITE:
        return state.entity_exists and state.invite_count == 0
    allowed = ", ".join(INSPECT_FILTERS)
    raise ValueError(f"Unknown inspect filter: {inspect_filter}; expected one of {allowed}")


def filter_inspection_states(states: list[AuthBusinessState], inspect_filter: str) -> list[AuthBusinessState]:
    """Return inspected states matching the active post-read inspection filter."""
    return [state for state in states if auth_state_matches_inspect_filter(state, inspect_filter)]


@dataclass(frozen=True)
class VerificationResult:
    """Per-candidate verify-auth result for enabled checks and buckets."""

    business_identifier: str
    entity_exists: bool
    entity_success: bool | None = None
    contact_success: bool | None = None
    affiliation_success: bool | None = None
    invite_success: bool | None = None
    missing_elements: tuple[str, ...] = ()
    missing_reasons: tuple[str, ...] = ()
    scenario_buckets: tuple[str, ...] = ()
    blocked_by_missing_entity: bool = False
    entity_ids: tuple[str, ...] = ()
    contact_count: int = 0
    usable_contact_count: int = 0
    expected_account_ids: tuple[str, ...] = ()
    found_account_ids: tuple[str, ...] = ()
    missing_account_ids: tuple[str, ...] = ()
    invite_count: int = 0

    @property
    def success(self) -> bool:
        """Return True when every enabled selected check passed and nothing is blocked."""
        return not self.missing_elements and not self.blocked_by_missing_entity


def _coerce_int_setting(config: Any, attr_name: str) -> int:
    raw_value = getattr(config, attr_name, 0)
    try:
        return int(raw_value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{attr_name} must be a valid integer") from exc


def _coerce_bool_setting(config: Any, attr_name: str, default: bool = False) -> bool:
    raw_value = getattr(config, attr_name, default)
    if isinstance(raw_value, bool):
        return raw_value
    if raw_value is None:
        return default
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"true", "1"}
    return bool(raw_value)


def blank_to_none(value: Any) -> str | None:
    """Return a stripped config string, or None for unset/blank values."""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


# Backwards-compatible private alias for existing callers/tests.
_blank_to_none = blank_to_none


def is_csv_like_output_root(path: str) -> bool:
    """Return True when a root value looks like an old-style CSV file path."""
    return path.rstrip("/\\").lower().endswith(".csv")


# Backwards-compatible private alias for existing callers/tests.
_is_csv_like_output_root = is_csv_like_output_root


def _derive_output_paths_from_root(output_root: str) -> dict[str, str]:
    """Derive fixed report CSV paths under a configured output directory/root."""
    root_path = Path(output_root).expanduser()
    return {path_key: str(root_path / filename) for path_key, filename in _DERIVED_OUTPUT_FILENAMES.items()}


def _resolve_output_paths(config: Any) -> dict[str, str]:
    """Resolve concrete output file paths from the single configured output root."""
    output_root = blank_to_none(getattr(config, AUTH_OUTPUT_PATH_ATTR, None))
    if not output_root:
        raise ValueError(f"{AUTH_OUTPUT_PATH_ATTR} must be set")
    if is_csv_like_output_root(output_root):
        raise ValueError(f"{AUTH_OUTPUT_PATH_ATTR} must be a directory/root path, not a .csv file path")
    return _derive_output_paths_from_root(output_root)


def parse_console_limit(raw_value: Any, config_key: str, default: int = DEFAULT_VERIFY_AUTH_CONSOLE_LIMIT) -> ConsoleLimit:
    """Parse a console row/table preview limit.

    Accepted values are unset/blank (caller default), ``0`` (disabled), positive
    integers, and ``ALL`` (unbounded). The parser is intentionally local to this
    flow surface and does not broaden config.py boolean/int parsing behavior.
    """
    raw = blank_to_none(raw_value)
    if raw is None:
        if default <= 0:
            raise ValueError(f"Default {config_key} must be a positive integer")
        return ConsoleLimit(disabled=False, max_rows=default)

    normalized = raw.upper()
    if normalized == "ALL":
        return ConsoleLimit(disabled=False, max_rows=None)
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{config_key} must be 0, a positive integer, or ALL") from exc
    if parsed < 0:
        raise ValueError(f"{config_key} must be 0, a positive integer, or ALL")
    if parsed == 0:
        return ConsoleLimit(disabled=True, max_rows=0)
    return ConsoleLimit(disabled=False, max_rows=parsed)


def parse_inspect_filter(raw_value: Any, config_key: str = "INSPECT_AUTH_FILTER") -> str:
    """Parse an inspect filter value using the provided config key in errors."""
    raw = (blank_to_none(raw_value) or INSPECT_FILTER_ALL).upper()
    if raw not in INSPECT_FILTERS:
        allowed = ", ".join(INSPECT_FILTERS)
        raise ValueError(f"Unknown {config_key}: {raw}; expected one of {allowed}")
    return raw



def parse_auth_selection_mode(config: Any) -> AuthSelectionMode:
    raw = (getattr(config, "AUTH_SELECTION_MODE", "MIGRATION_FILTER") or "MIGRATION_FILTER").strip().upper()
    try:
        return AuthSelectionMode(raw)
    except Exception as exc:
        allowed = ", ".join(mode.value for mode in AuthSelectionMode)
        raise ValueError(f"Unknown AUTH_SELECTION_MODE: {raw}; expected one of {allowed}") from exc


# Backwards-compatible private alias for existing callers/tests.
_parse_selection_mode = parse_auth_selection_mode


def parse_positive_int_tuple(config: Any, attr_name: str) -> tuple[int, ...]:
    values = parse_positive_int_csv(getattr(config, attr_name, None), name=attr_name)
    return tuple(int(value) for value in values)


# Backwards-compatible private alias for existing callers/tests.
_parse_positive_int_tuple = parse_positive_int_tuple


def parse_manual_account_ids(config: Any) -> tuple[str, ...]:
    raw_env = getattr(config, "AUTH_AFFILIATION_ACCOUNT_IDS_RAW", None)
    if blank_to_none(raw_env) is not None:
        return tuple(parse_positive_int_csv(raw_env, name="AUTH_AFFILIATION_ACCOUNT_IDS"))

    raw_csv = getattr(config, "AUTH_AFFILIATION_ACCOUNT_IDS_CSV", None)
    if blank_to_none(raw_csv) is not None:
        return tuple(parse_positive_int_csv(raw_csv, name="AUTH_AFFILIATION_ACCOUNT_IDS"))

    configured = getattr(config, "AUTH_AFFILIATION_ACCOUNT_IDS", None)
    if configured:
        if isinstance(configured, str):
            return tuple(parse_positive_int_csv(configured, name="AUTH_AFFILIATION_ACCOUNT_IDS"))
        account_ids: list[str] = []
        for value in configured:
            account_id = int(value)
            if account_id <= 0:
                raise ValueError("AUTH_AFFILIATION_ACCOUNT_IDS must contain only positive integers")
            account_ids.append(str(account_id))
        return tuple(account_ids)

    return ()


# Backwards-compatible private alias for existing callers/tests.
_manual_account_ids = parse_manual_account_ids


def get_selected_checks(config: Any) -> tuple[str, ...]:
    """Return enabled verify-auth checks in stable order."""
    return tuple(
        check_name
        for check_name, attr_name in _CHECK_CONFIG_ATTRS.items()
        if _coerce_bool_setting(config, attr_name, False)
    )


def validate_config(config: Any) -> VerifyAuthSettings:
    """Validate verify-auth config before database connections are opened."""
    batches = _coerce_int_setting(config, "AUTH_REPORT_BATCHES")
    if batches <= 0:
        raise ValueError("AUTH_REPORT_BATCHES must be greater than 0")

    batch_size = _coerce_int_setting(config, "AUTH_REPORT_BATCH_SIZE")
    if batch_size <= 0:
        raise ValueError("AUTH_REPORT_BATCH_SIZE must be greater than 0")

    selected_checks = get_selected_checks(config)
    if not selected_checks:
        raise ValueError("At least one VERIFY_AUTH_CHECK_* option must be enabled")

    console_limit = parse_console_limit(
        getattr(config, "VERIFY_AUTH_CONSOLE_LIMIT", None),
        "VERIFY_AUTH_CONSOLE_LIMIT",
        DEFAULT_VERIFY_AUTH_CONSOLE_LIMIT,
    )

    paths = _resolve_output_paths(config)

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
                "Auth verification does not fall back to global MIG_GROUP_IDS/MIG_BATCH_IDS"
            )

    manual_account_ids: tuple[str, ...] = ()
    if selection_mode == AuthSelectionMode.MANUAL and CHECK_AFFILIATION in selected_checks:
        manual_account_ids = parse_manual_account_ids(config)
    if CHECK_AFFILIATION in selected_checks and selection_mode == AuthSelectionMode.MANUAL and not manual_account_ids:
        raise ValueError(
            "VERIFY_AUTH_CHECK_AFFILIATION=True with AUTH_SELECTION_MODE=MANUAL requires "
            "AUTH_AFFILIATION_ACCOUNT_IDS"
        )

    return VerifyAuthSettings(
        batches=batches,
        batch_size=batch_size,
        selected_checks=selected_checks,
        console_limit=console_limit,
        summary_path=paths[SUMMARY_PATH_KEY],
        detail_path=paths[DETAIL_PATH_KEY],
        scenario_path=paths[SCENARIO_PATH_KEY],
        selection_mode=selection_mode,
        auth_corp_nums=auth_corp_nums,
        auth_mig_group_ids=auth_mig_group_ids,
        auth_mig_batch_ids=auth_mig_batch_ids,
        manual_account_ids=manual_account_ids,
    )


def build_candidate_queries(config: Any, settings: AuthCandidateSettings | None = None) -> CandidateQueries:
    """Build aligned count/page candidate queries from Auth targeting semantics."""
    settings = settings or validate_config(config)
    base_sql = get_auth_selected_corp_nums_query(
        config,
        settings.selection_mode,
        auth_corp_nums=settings.auth_corp_nums,
        auth_mig_group_ids=settings.auth_mig_group_ids,
        auth_mig_batch_ids=settings.auth_mig_batch_ids,
    ).strip()

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

    return CandidateQueries(base_sql=base_sql, count_sql=count_sql, page_sql=page_sql)


def get_candidate_count(
    config: Any,
    colin_extract_engine: Engine,
    settings: AuthCandidateSettings | None = None,
) -> int:
    """Execute the selected-candidate count query on the COLIN extract engine."""
    queries = build_candidate_queries(config, settings)
    with colin_extract_engine.connect() as conn:
        return int(conn.execute(queries.count_statement()).scalar() or 0)


def get_candidate_page(
    config: Any,
    colin_extract_engine: Engine,
    limit: int,
    offset: int,
    settings: AuthCandidateSettings | None = None,
) -> list[str]:
    """Execute the deterministic selected-candidate page query on the COLIN extract engine."""
    queries = build_candidate_queries(config, settings)
    with colin_extract_engine.connect() as conn:
        rows = conn.execute(queries.page_statement(), {"limit": int(limit), "offset": int(offset)}).fetchall()
    return [str(_row_value(row, 0, "corp_num")) for row in rows]


def _expected_accounts_query(config: Any, settings: AuthCandidateSettings, corp_nums: Iterable[str]) -> ExpectedAccountsQuery:
    """Build a COLIN-extract query deriving migration expected-account IDs for a candidate page."""
    normalized_corp_nums = [str(corp_num) for corp_num in corp_nums]
    params: dict[str, Any] = {
        "target_environment": getattr(config, "DATA_LOAD_ENV", ""),
        "corp_nums": normalized_corp_nums,
    }
    expanding_bind_names = ["corp_nums"]
    filters = [
        "mca.target_environment = :target_environment",
        "mca.corp_num IN :corp_nums",
    ]

    if settings.auth_mig_batch_ids:
        filters.append("b.id IN :auth_mig_batch_ids")
        params["auth_mig_batch_ids"] = list(settings.auth_mig_batch_ids)
        expanding_bind_names.append("auth_mig_batch_ids")
    if settings.auth_mig_group_ids:
        filters.append("b.mig_group_id IN :auth_mig_group_ids")
        params["auth_mig_group_ids"] = list(settings.auth_mig_group_ids)
        expanding_bind_names.append("auth_mig_group_ids")

    sql = f"""
        SELECT DISTINCT
            mca.corp_num,
            mca.account_id
        FROM mig_corp_account mca
        JOIN mig_batch b ON b.id = mca.mig_batch_id
        WHERE {' AND '.join(filters)}
        ORDER BY mca.corp_num, mca.account_id
    """.strip()

    return ExpectedAccountsQuery(sql=sql, params=params, expanding_bind_names=tuple(expanding_bind_names))


def build_expected_accounts_query(
    config: Any,
    corp_nums: Iterable[str],
    settings: AuthCandidateSettings | None = None,
) -> ExpectedAccountsQuery | None:
    """Return migration expected-account SQL, or None when manual accounts are configured.

    Manual mode intentionally does not read account IDs from the database; the existing
    AUTH_AFFILIATION_ACCOUNT_IDS config is the expected account set for every candidate.
    """
    settings = settings or validate_config(config)
    if settings.selection_mode == AuthSelectionMode.MANUAL:
        return None
    return _expected_accounts_query(config, settings, corp_nums)


def read_expected_accounts_for_candidates(
    config: Any,
    colin_extract_engine: Engine,
    corp_nums: Iterable[str],
    settings: AuthCandidateSettings | None = None,
) -> dict[str, tuple[str, ...]]:
    """Return expected affiliation account IDs per candidate business identifier.

    In MIGRATION_FILTER mode, this reads ``mig_corp_account`` from the COLIN extract
    engine and returns an empty tuple for page candidates with no derived accounts.
    In MANUAL mode, the existing ``AUTH_AFFILIATION_ACCOUNT_IDS`` values are reused
    for every candidate without opening a database connection.
    """
    settings = settings or validate_config(config)
    candidates = [str(corp_num) for corp_num in corp_nums]
    if not candidates:
        return {}

    if settings.selection_mode == AuthSelectionMode.MANUAL:
        return {corp_num: settings.manual_account_ids for corp_num in candidates}

    query = _expected_accounts_query(config, settings, candidates)
    expected: dict[str, set[str]] = {corp_num: set() for corp_num in candidates}
    with colin_extract_engine.connect() as conn:
        rows = conn.execute(query.statement(), query.params).fetchall()

    for row in rows:
        corp_num = str(_row_value(row, 0, "corp_num"))
        account_id = _row_value(row, 1, "account_id")
        if account_id is not None and corp_num in expected:
            expected[corp_num].add(str(account_id))

    return {corp_num: tuple(sorted(accounts, key=_numeric_sort_key)) for corp_num, accounts in expected.items()}


def _numeric_sort_key(value: str) -> tuple[int, str]:
    return (int(value), value) if value.isdigit() else (0, value)


def _build_text_statement(sql: str, expanding_bind_names: tuple[str, ...]) -> TextClause:
    """Return a SQLAlchemy text statement with expanding bind parameters attached."""
    stmt = text(sql)
    for bind_name in expanding_bind_names:
        stmt = stmt.bindparams(bindparam(bind_name, expanding=True))
    return stmt


def build_auth_entity_read_statement(business_identifiers: Iterable[str]) -> AuthReadStatement:
    """Build the read-only entity lookup statement for selected identifiers."""
    return AuthReadStatement(
        sql=_ENTITY_READ_SQL,
        params={"business_identifiers": [str(identifier) for identifier in business_identifiers]},
        expanding_bind_names=("business_identifiers",),
    )


def _build_entity_id_statement(sql: str, entity_ids: Iterable[Any]) -> AuthReadStatement:
    return AuthReadStatement(
        sql=sql,
        params={"entity_ids": list(entity_ids)},
        expanding_bind_names=("entity_ids",),
    )


def _sorted_unique_strings(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if value is not None}, key=_numeric_sort_key))


def _execute_fetchall(conn: Any, read_statement: AuthReadStatement) -> list[Any]:
    return list(conn.execute(read_statement.statement(), read_statement.params).fetchall())


def read_auth_states_for_candidates(
    auth_engine: Engine,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    selected_checks: tuple[str, ...] = _ALL_CHECKS,
) -> list[AuthBusinessState]:
    """Read and aggregate Auth DB state for selected candidates.

    The helper intentionally performs focused per-table reads and aggregates in
    Python. It reads entities first, then only reads dependent tables for found
    entity IDs and enabled dependent checks. No Auth API calls, writes, or
    auth_processing reservations are performed.
    """
    candidates = [str(identifier) for identifier in business_identifiers]
    if not candidates:
        return []

    expected_accounts_by_identifier = expected_accounts_by_identifier or {}
    entity_ids_by_identifier: dict[str, set[Any]] = {identifier: set() for identifier in candidates}
    business_names_by_identifier: dict[str, set[str]] = {identifier: set() for identifier in candidates}
    identifier_by_entity_id: dict[str, str] = {}
    contact_count_by_entity_id: dict[str, int] = defaultdict(int)
    usable_contact_count_by_entity_id: dict[str, int] = defaultdict(int)
    found_accounts_by_identifier: dict[str, set[str]] = {identifier: set() for identifier in candidates}
    found_account_names_by_identifier: dict[str, set[str]] = {identifier: set() for identifier in candidates}
    invite_count_by_entity_id: dict[str, int] = defaultdict(int)

    with auth_engine.connect() as conn:
        entity_rows = _execute_fetchall(conn, build_auth_entity_read_statement(candidates))
        for row in entity_rows:
            entity_id = _row_value(row, 0, "id", "entity_id")
            identifier = str(_row_value(row, 1, "business_identifier"))
            if identifier not in entity_ids_by_identifier or entity_id is None:
                continue
            entity_ids_by_identifier[identifier].add(entity_id)
            business_name = _row_value_or_none(row, 2, "business_name", "name")
            if business_name is not None and str(business_name).strip():
                business_names_by_identifier[identifier].add(str(business_name).strip())
            identifier_by_entity_id[str(entity_id)] = identifier

        entity_ids = [entity_id for entity_ids_set in entity_ids_by_identifier.values() for entity_id in entity_ids_set]
        if entity_ids and CHECK_CONTACT in selected_checks:
            contact_rows = _execute_fetchall(conn, _build_entity_id_statement(_CONTACT_READ_SQL, entity_ids))
            for row in contact_rows:
                entity_id = str(_row_value(row, 0, "entity_id"))
                contact_count_by_entity_id[entity_id] += 1
                email = _row_value(row, 2, "email")
                if email is not None and str(email).strip():
                    usable_contact_count_by_entity_id[entity_id] += 1

        if entity_ids and CHECK_AFFILIATION in selected_checks:
            affiliation_rows = _execute_fetchall(conn, _build_entity_id_statement(_AFFILIATION_READ_SQL, entity_ids))
            for row in affiliation_rows:
                entity_id = str(_row_value(row, 0, "entity_id"))
                identifier = identifier_by_entity_id.get(entity_id)
                org_id = _row_value(row, 1, "org_id")
                org_name = _row_value_or_none(row, 2, "org_name", "name")
                if identifier is not None and org_id is not None:
                    found_accounts_by_identifier[identifier].add(str(org_id))
                    if org_name is not None and str(org_name).strip():
                        found_account_names_by_identifier[identifier].add(str(org_name).strip())

        if entity_ids and CHECK_INVITE in selected_checks:
            invite_rows = _execute_fetchall(conn, _build_entity_id_statement(_INVITE_READ_SQL, entity_ids))
            for row in invite_rows:
                entity_id = str(_row_value(row, 0, "entity_id"))
                invite_count = _row_value(row, 1, "invite_count")
                invite_count_by_entity_id[entity_id] += int(invite_count or 0)

    states: list[AuthBusinessState] = []
    for identifier in candidates:
        entity_ids = _sorted_unique_strings(entity_ids_by_identifier.get(identifier, ()))
        business_names = _sorted_unique_strings(business_names_by_identifier.get(identifier, ()))
        expected_account_ids = _sorted_unique_strings(expected_accounts_by_identifier.get(identifier, ()))
        found_account_ids = _sorted_unique_strings(found_accounts_by_identifier.get(identifier, ()))
        found_account_names = _sorted_unique_strings(found_account_names_by_identifier.get(identifier, ()))
        missing_account_ids = tuple(
            account_id for account_id in expected_account_ids if account_id not in set(found_account_ids)
        )
        contact_count = sum(contact_count_by_entity_id.get(entity_id, 0) for entity_id in entity_ids)
        usable_contact_count = sum(usable_contact_count_by_entity_id.get(entity_id, 0) for entity_id in entity_ids)
        invite_count = sum(invite_count_by_entity_id.get(entity_id, 0) for entity_id in entity_ids)
        states.append(
            AuthBusinessState(
                business_identifier=identifier,
                business_names=business_names,
                entity_ids=entity_ids,
                contact_count=contact_count,
                usable_contact_count=usable_contact_count,
                expected_account_ids=expected_account_ids,
                found_account_ids=found_account_ids,
                found_account_names=found_account_names,
                missing_account_ids=missing_account_ids,
                invite_count=invite_count,
            )
        )
    return states


def build_verification_results(
    states: list[AuthBusinessState],
    selected_checks: tuple[str, ...],
) -> list[VerificationResult]:
    """Classify aggregated Auth DB state into selected-check results and buckets."""
    results: list[VerificationResult] = []
    for state in states:
        missing_elements: list[str] = []
        missing_reasons: list[str] = []
        scenario_buckets: list[str] = []
        found_account_set = set(state.found_account_ids)
        missing_account_ids = tuple(
            account_id for account_id in state.expected_account_ids if account_id not in found_account_set
        )
        blocked_by_missing_entity = False
        entity_success: bool | None = None
        contact_success: bool | None = None
        affiliation_success: bool | None = None
        invite_success: bool | None = None

        if CHECK_ENTITY in selected_checks:
            entity_success = state.entity_exists
            if not entity_success:
                missing_elements.append(CHECK_ENTITY)
                missing_reasons.append("entity_missing")

        if CHECK_CONTACT in selected_checks:
            if not state.entity_exists:
                contact_success = False
                blocked_by_missing_entity = True
                missing_elements.append(CHECK_CONTACT)
                missing_reasons.append("contact:entity_missing")
            else:
                contact_success = state.usable_contact_count > 0
                if not contact_success:
                    missing_elements.append(CHECK_CONTACT)
                    missing_reasons.append("contact:missing_usable_email")
                    scenario_buckets.append(SCENARIO_CONTACT_MISSING)

        if CHECK_AFFILIATION in selected_checks:
            if not state.entity_exists:
                affiliation_success = False
                blocked_by_missing_entity = True
                missing_elements.append(CHECK_AFFILIATION)
                missing_reasons.append("affiliation:entity_missing")
            elif not state.expected_account_ids:
                affiliation_success = False
                missing_elements.append(CHECK_AFFILIATION)
                missing_reasons.append("affiliation:no_expected_account_ids")
                scenario_buckets.append(SCENARIO_AFFILIATION_NO_EXPECTED)
            else:
                affiliation_success = not missing_account_ids
                if not affiliation_success:
                    missing_elements.append(CHECK_AFFILIATION)
                    missing_reasons.append("affiliation:missing_expected_accounts")
                    scenario_buckets.append(SCENARIO_AFFILIATION_MISSING)

        if CHECK_INVITE in selected_checks:
            if not state.entity_exists:
                invite_success = False
                blocked_by_missing_entity = True
                missing_elements.append(CHECK_INVITE)
                missing_reasons.append("invite:entity_missing")
            else:
                invite_success = state.invite_count > 0
                if not invite_success:
                    missing_elements.append(CHECK_INVITE)
                    missing_reasons.append("invite:missing")
                    scenario_buckets.append(SCENARIO_INVITE_MISSING)

        if missing_elements or blocked_by_missing_entity:
            scenario_buckets.insert(0, SCENARIO_MISSING_ANY)
            if not state.entity_exists and (CHECK_ENTITY in selected_checks or blocked_by_missing_entity):
                scenario_buckets.insert(1, SCENARIO_MISSING_ALL_AUTH_INFO)

        results.append(
            VerificationResult(
                business_identifier=state.business_identifier,
                entity_exists=state.entity_exists,
                entity_success=entity_success,
                contact_success=contact_success,
                affiliation_success=affiliation_success,
                invite_success=invite_success,
                missing_elements=tuple(dict.fromkeys(missing_elements)),
                missing_reasons=tuple(dict.fromkeys(missing_reasons)),
                scenario_buckets=tuple(dict.fromkeys(scenario_buckets)),
                blocked_by_missing_entity=blocked_by_missing_entity,
                entity_ids=state.entity_ids,
                contact_count=state.contact_count,
                usable_contact_count=state.usable_contact_count,
                expected_account_ids=state.expected_account_ids,
                found_account_ids=state.found_account_ids,
                missing_account_ids=missing_account_ids,
                invite_count=state.invite_count,
            )
        )
    return results


def run_auth_batch(
    config: Any,
    auth_engine: Engine,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> AuthBatchResult:
    """Read one configured candidate batch and optionally classify verification results."""
    settings = settings or validate_config(config)
    candidates = [str(identifier) for identifier in business_identifiers]
    if len(candidates) > settings.batch_size:
        raise ValueError(
            f"Auth batch contains {len(candidates)} candidates, exceeding configured "
            f"batch size {settings.batch_size}"
        )
    states = read_auth_states_for_candidates(
        auth_engine,
        candidates,
        expected_accounts_by_identifier=expected_accounts_by_identifier,
        selected_checks=settings.auth_read_checks,
    )
    verification_results = build_verification_results(states, settings.selected_checks) if settings.run_verify else []
    return AuthBatchResult(states=states, verification_results=verification_results)


def verify_auth_batch_result(
    config: Any,
    auth_engine: Engine,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> AuthBatchResult:
    """Read one configured candidate batch and return raw states plus verification results.

    Use this helper when callers need raw read-back rows from
    ``AuthBatchResult.states``. ``verify_auth_batch`` remains the convenience
    wrapper for verification results only.
    """
    return run_auth_batch(
        config,
        auth_engine,
        business_identifiers,
        expected_accounts_by_identifier,
        settings,
    )


def verify_auth_batch(
    config: Any,
    auth_engine: Engine,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> list[VerificationResult]:
    """Read and verify one configured candidate batch against Auth DB state.

    Returns verification results only. Use ``verify_auth_batch_result`` to access
    ``AuthBatchResult.states`` for shared read-back/inspection helpers.
    """
    return verify_auth_batch_result(
        config,
        auth_engine,
        business_identifiers,
        expected_accounts_by_identifier,
        settings,
    ).verification_results


def verify_auth_batch_result_from_config(
    config: Any,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> AuthBatchResult:
    """Initialize Auth DB via ``auth_init(config)`` and return the full Auth batch result."""
    from common.init_utils import auth_init  # Imported lazily to keep helper imports lightweight.

    auth_engine = auth_init(config)
    try:
        return verify_auth_batch_result(config, auth_engine, business_identifiers, expected_accounts_by_identifier, settings)
    finally:
        dispose_engine(auth_engine)


def verify_auth_batch_from_config(
    config: Any,
    business_identifiers: Iterable[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> list[VerificationResult]:
    """Initialize Auth DB via ``auth_init(config)`` and verify one read-only batch.

    Returns verification results only. Use ``verify_auth_batch_result_from_config``
    to access ``AuthBatchResult.states`` for shared read-back/inspection helpers.
    The engine is disposed in ``finally`` so callers that
    use this one-shot wrapper do not leak connection-pool resources after success
    or failure.
    """
    return verify_auth_batch_result_from_config(
        config,
        business_identifiers,
        expected_accounts_by_identifier,
        settings,
    ).verification_results


def build_summary_row(results: list[VerificationResult], selected_checks: tuple[str, ...]) -> dict[str, int]:
    """Build aggregate summary counts for all verification results."""
    summary = {
        "total_count": len(results),
        "success_count": sum(1 for result in results if result.success),
        "failure_count": sum(1 for result in results if not result.success),
        "missing_any_count": sum(1 for result in results if not result.success),
    }
    for check_name in selected_checks:
        summary[f"missing_{check_name}_count"] = sum(
            1 for result in results if check_name in result.missing_elements
        )
    if any(check_name in selected_checks for check_name in _DEPENDENT_CHECKS):
        summary["blocked_by_missing_entity_count"] = sum(
            1 for result in results if result.blocked_by_missing_entity
        )
    if CHECK_AFFILIATION in selected_checks:
        summary["affiliation_no_expected_accounts_count"] = sum(
            1 for result in results if SCENARIO_AFFILIATION_NO_EXPECTED in result.scenario_buckets
        )
    return summary


def summary_fieldnames(selected_checks: tuple[str, ...]) -> list[str]:
    """Return stable summary CSV fieldnames for enabled checks."""
    fieldnames = [*_SUMMARY_BASE_FIELDNAMES]
    fieldnames.extend(f"missing_{check_name}_count" for check_name in selected_checks)
    if any(check_name in selected_checks for check_name in _DEPENDENT_CHECKS):
        fieldnames.append("blocked_by_missing_entity_count")
    if CHECK_AFFILIATION in selected_checks:
        fieldnames.append("affiliation_no_expected_accounts_count")
    return fieldnames


def build_detail_rows(results: list[VerificationResult]) -> list[dict[str, str | int]]:
    """Build mismatch-only detail report rows."""
    rows: list[dict[str, str | int]] = []
    for result in results:
        if result.success:
            continue
        rows.append(
            {
                "business_identifier": result.business_identifier,
                "missing_elements": _format_tuple(result.missing_elements),
                "missing_reasons": _format_tuple(result.missing_reasons),
                "scenario_buckets": _format_tuple(result.scenario_buckets),
                "blocked_by_missing_entity": _format_bool(result.blocked_by_missing_entity),
                "entity_exists": _format_bool(result.entity_exists),
                "entity_success": _format_bool(result.entity_success),
                "contact_success": _format_bool(result.contact_success),
                "affiliation_success": _format_bool(result.affiliation_success),
                "invite_success": _format_bool(result.invite_success),
                "entity_ids": _format_tuple(result.entity_ids),
                "contact_count": result.contact_count,
                "usable_contact_count": result.usable_contact_count,
                "expected_account_ids": _format_tuple(result.expected_account_ids),
                "found_account_ids": _format_tuple(result.found_account_ids),
                "missing_account_ids": _format_tuple(result.missing_account_ids),
                "invite_count": result.invite_count,
            }
        )
    return rows


def build_scenario_rows(results: list[VerificationResult]) -> list[dict[str, str | int]]:
    """Build operational bucket rows for scenarios with missing identifiers."""
    identifiers_by_scenario: dict[str, list[str]] = {scenario: [] for scenario in SCENARIO_ORDER}
    for result in results:
        for scenario in result.scenario_buckets:
            if scenario in identifiers_by_scenario:
                identifiers_by_scenario[scenario].append(result.business_identifier)

    return [
        {
            "scenario": scenario,
            "count": len(identifiers_by_scenario[scenario]),
            "identifiers_csv": ",".join(identifiers_by_scenario[scenario]),
            "recommended_action": SCENARIO_RECOMMENDED_ACTIONS[scenario],
        }
        for scenario in SCENARIO_ORDER
        if identifiers_by_scenario[scenario]
    ]


def _dependent_state(entity_exists: bool, present: bool) -> str:
    if not entity_exists:
        return "not_applicable_entity_missing"
    return "present" if present else "missing"


def build_inspection_rows(states: list[AuthBusinessState]) -> list[dict[str, str | int]]:
    """Build factual inspection rows from the provided Auth DB states.

    ``contact_state`` is based on usable contacts with non-blank email; raw
    contact row totals remain available in ``contact_count``.
    """
    rows: list[dict[str, str | int]] = []
    for state in states:
        entity_exists = state.entity_exists
        rows.append(
            {
                "business_identifier": state.business_identifier,
                "business_names": _format_tuple(state.business_names),
                "entity_state": "present" if entity_exists else "missing",
                "entity_exists": _format_bool(entity_exists),
                "entity_count": len(state.entity_ids),
                "entity_ids": _format_tuple(state.entity_ids),
                "contact_state": _dependent_state(entity_exists, state.usable_contact_count > 0),
                "contact_count": state.contact_count,
                "usable_contact_count": state.usable_contact_count,
                "affiliation_state": _dependent_state(entity_exists, bool(state.found_account_ids)),
                "affiliation_count": len(state.found_account_ids),
                "found_account_ids": _format_tuple(state.found_account_ids),
                "found_account_names": _format_tuple(state.found_account_names),
                "expected_account_ids": _format_tuple(state.expected_account_ids),
                "missing_account_ids": _format_tuple(state.missing_account_ids),
                "invite_state": _dependent_state(entity_exists, state.invite_count > 0),
                "invite_count": state.invite_count,
                "blocked_by_missing_entity": _format_bool(not entity_exists),
            }
        )
    return rows


def build_inspection_identifier_rows(
    states: list[AuthBusinessState],
    matched_states: list[AuthBusinessState],
    inspect_filter: str,
) -> list[dict[str, str | int]]:
    """Build copy-friendly AUTH_CORP_NUMS rows from raw inspection state."""
    if inspect_filter != INSPECT_FILTER_ALL:
        return [
            {
                "inspect_filter": inspect_filter,
                "count": len(matched_states),
                "identifiers_csv": ",".join(state.business_identifier for state in matched_states),
            }
        ]

    rows: list[dict[str, str | int]] = []
    for filter_token in INSPECT_IDENTIFIER_FILTERS:
        identifiers = [
            state.business_identifier
            for state in states
            if auth_state_matches_inspect_filter(state, filter_token)
        ]
        if identifiers:
            rows.append(
                {
                    "inspect_filter": filter_token,
                    "count": len(identifiers),
                    "identifiers_csv": ",".join(identifiers),
                }
            )
    return rows


def _ensure_parent_dir(path: str) -> Path:
    expanded_path = Path(path).expanduser()
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    return expanded_path


def write_summary_csv(path: str, results: list[VerificationResult], selected_checks: tuple[str, ...]) -> None:
    """Write the aggregate summary CSV report."""
    fieldnames = summary_fieldnames(selected_checks)
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(build_summary_row(results, selected_checks))


def write_detail_csv(path: str, results: list[VerificationResult]) -> None:
    """Write mismatch-only detail CSV rows, including headers when there are no mismatches."""
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=DETAIL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(build_detail_rows(results))


def _format_sql_quoted_identifier_list(identifiers_csv: Any) -> str:
    """Return identifiers as a SQL-friendly single-quoted comma-delimited list."""
    identifiers = _split_identifiers_csv(identifiers_csv)
    return ",".join("'" + identifier.replace("'", "''") + "'" for identifier in identifiers)


def _write_identifier_copy_list_section(
    txt_file: Any,
    rows: list[dict[str, str | int]],
    *,
    label_key: str,
    title: str,
    action_key: str | None = None,
) -> None:
    """Write copy-friendly AUTH_CORP_NUMS lists to an open text file."""
    txt_file.write(f"# {title}\n")
    txt_file.write("# Copy the AUTH_CORP_NUMS=... line for the group you want to run.\n")
    if not rows:
        txt_file.write("# No identifier groups emitted.\n")
        return
    for row in rows:
        label = str(row[label_key])
        count = row.get("count", 0)
        txt_file.write("\n")
        txt_file.write(f"[{label}] count={count}\n")
        if action_key and row.get(action_key):
            txt_file.write(f"# {row[action_key]}\n")
        identifiers_csv = row.get("identifiers_csv", "")
        txt_file.write(f"AUTH_CORP_NUMS={identifiers_csv}\n")
        txt_file.write("\n")
        txt_file.write("# SQL IN (...) fragment value for manual database queries.\n")
        txt_file.write(f"SQL_IN_IDENTIFIERS={_format_sql_quoted_identifier_list(identifiers_csv)}\n")


def _write_identifier_copy_list_txt(
    path: str,
    rows: list[dict[str, str | int]],
    *,
    label_key: str,
    title: str,
    action_key: str | None = None,
) -> None:
    """Write copy-friendly AUTH_CORP_NUMS lists as plain text."""
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", encoding="utf-8") as txt_file:
        _write_identifier_copy_list_section(
            txt_file,
            rows,
            label_key=label_key,
            title=title,
            action_key=action_key,
        )


def write_scenario_txt(path: str, results: list[VerificationResult]) -> None:
    """Write operational scenario summary and identifier copy lists as plain text."""
    scenario_rows = build_scenario_rows(results)
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", encoding="utf-8") as txt_file:
        txt_file.write("# Verify Auth scenario summary\n")
        if scenario_rows:
            summary_columns = ("scenario", "count", "recommended_action")
            table_rows = [{column: str(row.get(column, "")) for column in summary_columns} for row in scenario_rows]
            for line in _render_table_lines(table_rows, summary_columns, right_aligned_columns=("count",)):
                txt_file.write(f"{line}\n")
        else:
            txt_file.write("# No populated scenario buckets.\n")
        txt_file.write("\n")
        _write_identifier_copy_list_section(
            txt_file,
            scenario_rows,
            label_key="scenario",
            title="Verify Auth scenario identifier copy lists",
            action_key="recommended_action",
        )


def write_inspection_csv(path: str, states: list[AuthBusinessState]) -> None:
    """Write factual Auth DB inspection detail CSV rows for the provided states."""
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=INSPECTION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(build_inspection_rows(states))


_INSPECTION_FILTER_SUMMARY_METRICS = {
    INSPECT_FILTER_HAS_ANY_AUTH: ("HasAnyAuth", "has_any_auth_count"),
    INSPECT_FILTER_MISSING_ENTITY: ("MissingEntity", "missing_entity_count"),
    INSPECT_FILTER_HAS_ENTITY: ("HasEntity", "has_entity_count"),
    INSPECT_FILTER_HAS_CONTACT: ("HasUsableContactEmail", "has_contact_count"),
    INSPECT_FILTER_ENTITY_WITHOUT_CONTACT: (
        "EntityWithoutUsableContactEmail",
        "entity_without_contact_count",
    ),
    INSPECT_FILTER_HAS_AFFILIATION: ("HasAffiliation", "has_affiliation_count"),
    INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION: (
        "EntityWithoutAffiliation",
        "entity_without_affiliation_count",
    ),
    INSPECT_FILTER_HAS_INVITE: ("HasInvite", "has_invite_count"),
    INSPECT_FILTER_ENTITY_WITHOUT_INVITE: ("EntityWithoutInvite", "entity_without_invite_count"),
}


def _all_inspection_summary_metric_rows(summary: dict[str, int | str]) -> list[tuple[str, int | str]]:
    """Return display-ordered full inspect summary metric rows."""
    return [
        ("Inspected", summary.get("inspected_count", 0)),
        ("MatchedByFilter", summary.get("matched_count", 0)),
        ("HasAnyAuth", summary.get("has_any_auth_count", 0)),
        ("MissingEntity", summary.get("missing_entity_count", 0)),
        ("HasEntity", summary.get("has_entity_count", 0)),
        ("HasUsableContactEmail", summary.get("has_contact_count", 0)),
        ("EntityWithoutUsableContactEmail", summary.get("entity_without_contact_count", 0)),
        ("HasAffiliation", summary.get("has_affiliation_count", 0)),
        ("EntityWithoutAffiliation", summary.get("entity_without_affiliation_count", 0)),
        ("HasInvite", summary.get("has_invite_count", 0)),
        ("EntityWithoutInvite", summary.get("entity_without_invite_count", 0)),
    ]


def _inspection_summary_metric_rows(summary: dict[str, int | str]) -> list[tuple[str, int | str]]:
    """Return filter-aware inspect summary metric rows."""
    inspect_filter = str(summary.get("inspect_filter", INSPECT_FILTER_ALL))
    if inspect_filter == INSPECT_FILTER_ALL:
        return _all_inspection_summary_metric_rows(summary)

    rows: list[tuple[str, int | str]] = [
        ("Inspected", summary.get("inspected_count", 0)),
        ("MatchedByFilter", summary.get("matched_count", 0)),
    ]
    filter_metric = _INSPECTION_FILTER_SUMMARY_METRICS.get(inspect_filter)
    if filter_metric:
        label, summary_key = filter_metric
        rows.append((label, summary.get(summary_key, 0)))
    return rows


def write_inspection_summary_txt(
    path: str,
    identifier_rows: list[dict[str, str | int]],
    summary: dict[str, int | str] | None = None,
) -> None:
    """Write inspect summary and copy-friendly identifier groups as plain text."""
    expanded_path = _ensure_parent_dir(path)
    with open(expanded_path, "w", encoding="utf-8") as txt_file:
        if summary is not None:
            txt_file.write("# Inspect Auth summary\n")
            txt_file.write(f"Filter={summary.get('inspect_filter', '')}\n")
            table_rows = [
                {"metric": label, "count": str(value)}
                for label, value in _inspection_summary_metric_rows(summary)
            ]
            for line in _render_table_lines(table_rows, ("metric", "count"), right_aligned_columns=("count",)):
                txt_file.write(f"{line}\n")
            txt_file.write("\n")

        _write_identifier_copy_list_section(
            txt_file,
            identifier_rows,
            label_key="inspect_filter",
            title="Inspect Auth identifier copy lists",
        )


def _table_header_border(widths: dict[str, int], columns: tuple[str, ...]) -> str:
    """Return a strong separator sized to the rendered table header."""
    return "─┼─".join("─" * widths[column] for column in columns)


def _render_table_lines(
    table_rows: list[dict[str, str]],
    columns: tuple[str, ...],
    *,
    right_aligned_columns: tuple[str, ...] = (),
) -> list[str]:
    """Return rendered table lines using the same header style as console tables."""
    widths = {
        column: max(len(column), *(len(row[column]) for row in table_rows))
        for column in columns
    }
    header_border = _table_header_border(widths, columns)
    lines = [
        header_border,
        " | ".join(column.ljust(widths[column]) for column in columns),
        header_border,
    ]
    for row in table_rows:
        lines.append(
            " | ".join(
                row[column].rjust(widths[column]) if column in right_aligned_columns else row[column].ljust(widths[column])
                for column in columns
            )
        )
    return lines


def print_scenario_summary_rows(scenario_rows: list[dict[str, str | int]]) -> None:
    """Print a compact scenario bucket summary without long identifier lists."""
    if not scenario_rows:
        print("✅ Verify Auth scenario summary: no populated scenario buckets.")
        return

    summary_columns = ("scenario", "count", "recommended_action")
    table_rows = [{column: str(row.get(column, "")) for column in summary_columns} for row in scenario_rows]
    widths = {
        column: max(len(column), *(len(row[column]) for row in table_rows))
        for column in summary_columns
    }

    header_border = _table_header_border(widths, summary_columns)
    print("🧭 Verify Auth scenario summary:")
    print(header_border)
    print(" | ".join(column.ljust(widths[column]) for column in summary_columns))
    print(header_border)
    for row in table_rows:
        print(
            " | ".join(
                row[column].rjust(widths[column]) if column == "count" else row[column].ljust(widths[column])
                for column in summary_columns
            )
        )


def _console_limit_value(console_limit: ConsoleLimit | None) -> str:
    """Return the configured console limit value used for operator-facing output."""
    if console_limit is None or console_limit.max_rows is None:
        return "ALL"
    if console_limit.disabled:
        return "0"
    return str(console_limit.max_rows)


def _console_cap_label(console_limit: ConsoleLimit | None, limit_config_key: str, *, unit: str) -> str:
    """Return a short human-readable label for console cap state."""
    configured_limit = _console_limit_value(console_limit)
    if configured_limit == "ALL":
        return f"console cap: ALL {unit}; ConfiguredConsoleLimit=ALL"
    if configured_limit == "0":
        return f"console cap: 0 {unit}; ConfiguredConsoleLimit=0"
    return (
        f"console cap: {configured_limit} {unit}; "
        f"ConfiguredConsoleLimit={configured_limit}; set {limit_config_key}=ALL for full console output"
    )


def _split_identifiers_csv(value: Any) -> list[str]:
    """Split a comma-delimited identifier cell into non-blank identifier tokens."""
    return [token.strip() for token in str(value or "").split(",") if token.strip()]


def _limited_identifiers(
    identifiers: list[str],
    console_limit: ConsoleLimit | None,
) -> tuple[list[str], bool]:
    """Return identifiers to print and whether output was truncated."""
    if console_limit is None or console_limit.max_rows is None:
        return identifiers, False
    if console_limit.disabled:
        return [], bool(identifiers)
    max_rows = max(console_limit.max_rows, 0)
    shown = identifiers[:max_rows]
    return shown, len(identifiers) > len(shown)


def _format_identifier_console_list(identifiers: list[str], *, truncated: bool) -> str:
    """Return a copy-list preview, visibly marked when capped."""
    rendered = ",".join(identifiers)
    if not truncated:
        return rendered
    return f"{rendered},..." if rendered else "..."


def _format_sql_identifier_console_list(identifiers: list[str], *, truncated: bool) -> str:
    """Return a SQL-friendly identifier preview, visibly marked when capped."""
    rendered = _format_sql_quoted_identifier_list(",".join(identifiers))
    if not truncated:
        return rendered
    return f"{rendered},..." if rendered else "..."


def _copy_list_guidance(copy_list_path: str | None, fallback_filename: str) -> str:
    """Return explicit operator guidance for complete copy lists."""
    if copy_list_path:
        return f"Copy the full list from CopyListPath={copy_list_path}."
    return f"Copy the full list from {fallback_filename}."


def _print_identifier_group_block(
    *,
    label_name: str,
    label_value: str,
    count: Any,
    identifiers_preview: str,
    sql_identifiers_preview: str,
) -> None:
    """Print one visually separated identifier copy-list group."""
    print()
    print(IDENTIFIER_GROUP_SEPARATOR)
    print(f"{label_name}: {label_value}  |  Count: {count}")
    print("AUTH_CORP_NUMS identifiers:")
    print(identifiers_preview)
    print("SQL IN identifiers:")
    print(sql_identifiers_preview)


def _bold_red(text: str) -> str:
    """Return text styled as bold red for console warning labels."""
    return f"{ANSI_BOLD_RED}{text}{ANSI_RESET}"


def _print_identifier_cap_warning(
    *,
    label: str,
    bucket_name: str,
    total_identifiers: int,
    identifiers_shown: int,
    configured_console_limit: str,
    copy_list_path: str | None,
    fallback_filename: str,
    limit_config_key: str,
) -> None:
    """Print high-visibility guidance when identifier console output is capped."""
    print(f"🚫 {_bold_red('DO NOT COPY FROM CONSOLE')}: AUTH_CORP_NUMS list below/above is capped and INCOMPLETE.")
    print(
        f"⚠️ {label} capped by {limit_config_key}. "
        f"ConfiguredConsoleLimit={configured_console_limit}. "
        f"{bucket_name}, TotalIdentifiers={total_identifiers}, IdentifiersShown={identifiers_shown}."
    )
    print(f"✅ {_copy_list_guidance(copy_list_path, fallback_filename)}")
    print(f"🔧 Set {limit_config_key}=ALL only if you intentionally want the full list printed in console.")


def _print_scenario_identifier_truncated_message(
    scenario: str,
    total_identifiers: int,
    identifiers_shown: int,
    copy_list_path: str | None,
    limit_config_key: str,
    configured_console_limit: str,
) -> None:
    """Print guidance when verify scenario identifier console output is truncated."""
    _print_identifier_cap_warning(
        label="Verify Auth scenario identifiers console output",
        bucket_name=f"Scenario={scenario}",
        total_identifiers=total_identifiers,
        identifiers_shown=identifiers_shown,
        configured_console_limit=configured_console_limit,
        copy_list_path=copy_list_path,
        fallback_filename="verify-auth-scenario.txt",
        limit_config_key=limit_config_key,
    )


def print_scenario_rows(
    scenario_rows: list[dict[str, str | int]],
    console_limit: ConsoleLimit | None = None,
    copy_list_path: str | None = None,
    limit_config_key: str = "VERIFY_AUTH_CONSOLE_LIMIT",
) -> None:
    """Print copy-friendly scenario bucket identifiers from already-built scenario rows."""
    if console_limit is not None and console_limit.disabled:
        return

    if not scenario_rows:
        print("✅ Verify Auth scenario identifiers: no identifiers to copy into AUTH_CORP_NUMS.")
        return

    cap_label = _console_cap_label(console_limit, limit_config_key, unit="identifiers per bucket")
    print(f"📋 Verify Auth scenario identifiers for AUTH_CORP_NUMS ({cap_label}):")
    for row in scenario_rows:
        scenario = str(row["scenario"])
        identifiers = _split_identifiers_csv(row.get("identifiers_csv", ""))
        identifiers_to_print, truncated = _limited_identifiers(identifiers, console_limit)
        _print_identifier_group_block(
            label_name="Scenario",
            label_value=scenario,
            count=row["count"],
            identifiers_preview=_format_identifier_console_list(identifiers_to_print, truncated=truncated),
            sql_identifiers_preview=_format_sql_identifier_console_list(identifiers_to_print, truncated=truncated),
        )
        if truncated:
            _print_scenario_identifier_truncated_message(
                scenario=scenario,
                total_identifiers=len(identifiers),
                identifiers_shown=len(identifiers_to_print),
                copy_list_path=copy_list_path,
                limit_config_key=limit_config_key,
                configured_console_limit=_console_limit_value(console_limit),
            )


def build_inspection_summary(states: list[AuthBusinessState], matched_states: list[AuthBusinessState], inspect_filter: str) -> dict[str, int | str]:
    """Build full-population inspection summary counts.

    ``has_contact_count`` and ``entity_without_contact_count`` use usable contact
    email, not merely raw contact row presence.
    """
    return {
        "inspect_filter": inspect_filter,
        "inspected_count": len(states),
        "matched_count": len(matched_states),
        "emitted_count": len(matched_states),
        "has_any_auth_count": sum(1 for state in states if auth_state_has_any_auth(state)),
        "missing_entity_count": sum(1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_MISSING_ENTITY)),
        "has_entity_count": sum(1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_HAS_ENTITY)),
        "has_contact_count": sum(1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_HAS_CONTACT)),
        "entity_without_contact_count": sum(
            1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_ENTITY_WITHOUT_CONTACT)
        ),
        "has_affiliation_count": sum(1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_HAS_AFFILIATION)),
        "entity_without_affiliation_count": sum(
            1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION)
        ),
        "has_invite_count": sum(1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_HAS_INVITE)),
        "entity_without_invite_count": sum(
            1 for state in states if auth_state_matches_inspect_filter(state, INSPECT_FILTER_ENTITY_WITHOUT_INVITE)
        ),
    }


def print_inspection_summary(states: list[AuthBusinessState], matched_states: list[AuthBusinessState], inspect_filter: str) -> None:
    """Print readable summary-first inspection output."""
    summary = build_inspection_summary(states, matched_states, inspect_filter)
    metric_rows = [(label, str(value)) for label, value in _inspection_summary_metric_rows(summary)]
    metric_width = max(len("metric"), *(len(label) for label, _ in metric_rows))
    count_width = max(len("count"), *(len(value) for _, value in metric_rows))
    header_border = f"{'─' * metric_width}─┼─{'─' * count_width}"

    print(f"🔎 Inspect Auth summary (Filter={summary['inspect_filter']}):")
    print(header_border)
    print(f"{'metric'.ljust(metric_width)} | {'count'.rjust(count_width)}")
    print(header_border)
    for label, value in metric_rows:
        print(f"{label.ljust(metric_width)} | {value.rjust(count_width)}")
    print()
    if not states:
        print("🔎 Inspect Auth: no selected businesses to inspect.")
    elif not matched_states:
        print("🔎 Inspect Auth: no rows matched the active inspect filter.")


def _preview_rows(rows: list[dict[str, str | int]], console_limit: ConsoleLimit | None) -> list[dict[str, str | int]]:
    """Return rows permitted by a console preview limit."""
    if console_limit is None or console_limit.max_rows is None:
        return rows
    if console_limit.disabled:
        return []
    return rows[: console_limit.max_rows]


def _print_preview_truncated_message(
    *,
    label: str,
    total_rows: int,
    shown_rows: int,
    report_path: str | None,
    limit_config_key: str,
) -> None:
    """Print standard guidance when a row/table preview is truncated."""
    path_fragment = f" ReportPath={report_path}." if report_path else ""
    print(
        f"⚠️ {label} console preview capped by {limit_config_key}. "
        f"ConfiguredConsoleLimit={shown_rows}. TotalRows={total_rows}, RowsShown={shown_rows}."
        f"{path_fragment} Set {limit_config_key}=ALL to print all preview rows, or 0 to suppress previews."
    )


def print_inspection_rows(
    inspection_rows: list[dict[str, str | int]],
    console_limit: ConsoleLimit | None = None,
    report_path: str | None = None,
    limit_config_key: str = "INSPECT_AUTH_CONSOLE_LIMIT",
) -> None:
    """Print a compact factual inspection table for matched inspection rows."""
    if console_limit is not None and console_limit.disabled:
        return
    if not inspection_rows:
        print("🔎 Inspect Auth detail: no matched rows to print.")
        return

    preview_rows = _preview_rows(inspection_rows, console_limit)
    if not preview_rows:
        return

    columns = (
        "business_identifier",
        "business_names",
        "entity_state",
        "contact_state",
        "affiliation_state",
        "invite_state",
        "found_account_ids",
        "found_account_names",
    )
    table_rows = [{column: str(row.get(column, "")) for column in columns} for row in preview_rows]
    truncated = len(preview_rows) < len(inspection_rows)
    if truncated:
        remaining_rows = len(inspection_rows) - len(preview_rows)
        table_rows.append(
            {
                "business_identifier": f"⚠️ {remaining_rows} MORE ROWS NOT SHOWN",
                "business_names": f"console capped by {limit_config_key}",
                "entity_state": "CSV complete",
                "contact_state": "set ALL",
                "affiliation_state": "for full console",
                "invite_state": "",
                "found_account_ids": "",
                "found_account_names": "",
            }
        )
    widths = {
        column: max(len(column), *(len(row[column]) for row in table_rows))
        for column in columns
    }

    cap_label = _console_cap_label(console_limit, limit_config_key, unit="rows")
    header_border = _table_header_border(widths, columns)
    marker_separator = "-+-".join("-" * widths[column] for column in columns)
    print(f"🔎 Inspect Auth state (contact_state uses usable contact email; {cap_label}):")
    print(header_border)
    print(" | ".join(column.ljust(widths[column]) for column in columns))
    print(header_border)
    for row in table_rows:
        rendered_row = " | ".join(row[column].ljust(widths[column]) for column in columns)
        if row["business_identifier"].startswith("⚠️ "):
            print(marker_separator)
            print(rendered_row)
            print(marker_separator)
        else:
            print(rendered_row)

    if truncated:
        _print_preview_truncated_message(
            label="Inspect Auth state",
            total_rows=len(inspection_rows),
            shown_rows=len(preview_rows),
            report_path=report_path,
            limit_config_key=limit_config_key,
        )


def _print_inspection_identifier_truncated_message(
    inspect_filter: str,
    total_identifiers: int,
    identifiers_shown: int,
    copy_list_path: str | None,
    limit_config_key: str,
    configured_console_limit: str,
) -> None:
    """Print guidance when inspect identifier console output is truncated."""
    _print_identifier_cap_warning(
        label="Inspect Auth identifiers console output",
        bucket_name=f"Filter={inspect_filter}",
        total_identifiers=total_identifiers,
        identifiers_shown=identifiers_shown,
        configured_console_limit=configured_console_limit,
        copy_list_path=copy_list_path,
        fallback_filename="inspect-auth-summary.txt",
        limit_config_key=limit_config_key,
    )


def print_inspection_identifier_rows(
    identifier_rows: list[dict[str, str | int]],
    inspect_filter: str,
    console_limit: ConsoleLimit | None = None,
    copy_list_path: str | None = None,
    limit_config_key: str = "INSPECT_AUTH_CONSOLE_LIMIT",
) -> None:
    """Print copy-friendly inspect identifiers for AUTH_CORP_NUMS."""
    if console_limit is not None and console_limit.disabled:
        return

    if not identifier_rows:
        if inspect_filter != INSPECT_FILTER_ALL:
            print(
                "✅ Inspect Auth identifiers: "
                f"no identifiers matched {inspect_filter} for AUTH_CORP_NUMS."
            )
            return
        print("✅ Inspect Auth identifiers: no concrete inspect identifier groups to copy into AUTH_CORP_NUMS.")
        return

    if inspect_filter != INSPECT_FILTER_ALL and not int(identifier_rows[0]["count"]):
        print(
            "✅ Inspect Auth identifiers: "
            f"no identifiers matched {inspect_filter} for AUTH_CORP_NUMS."
        )
        return

    cap_label = _console_cap_label(console_limit, limit_config_key, unit="identifiers per group")
    print(f"📋 Inspect Auth identifiers for AUTH_CORP_NUMS ({cap_label}):")
    for row in identifier_rows:
        row_filter = str(row["inspect_filter"])
        identifiers = _split_identifiers_csv(row.get("identifiers_csv", ""))
        identifiers_to_print, truncated = _limited_identifiers(identifiers, console_limit)
        _print_identifier_group_block(
            label_name="Filter",
            label_value=row_filter,
            count=row["count"],
            identifiers_preview=_format_identifier_console_list(identifiers_to_print, truncated=truncated),
            sql_identifiers_preview=_format_sql_identifier_console_list(identifiers_to_print, truncated=truncated),
        )
        if truncated:
            _print_inspection_identifier_truncated_message(
                inspect_filter=row_filter,
                total_identifiers=len(identifiers),
                identifiers_shown=len(identifiers_to_print),
                copy_list_path=copy_list_path,
                limit_config_key=limit_config_key,
                configured_console_limit=_console_limit_value(console_limit),
            )


def write_verification_reports(settings: VerifyAuthSettings, results: list[VerificationResult]) -> None:
    """Write all configured verify-auth CSV reports."""
    if not (settings.summary_path and settings.detail_path and settings.scenario_path):
        raise ValueError("Verify report paths must be set before writing verification reports")
    write_summary_csv(settings.summary_path, results, settings.selected_checks)
    write_detail_csv(settings.detail_path, results)
    write_scenario_txt(settings.scenario_path, results)


def write_inspection_report(path: str, states: list[AuthBusinessState]) -> None:
    """Write an inspection CSV report to the provided path."""
    if not path:
        raise ValueError("Inspection output path must be set before writing inspection reports")
    write_inspection_csv(path, states)


def calculate_batch_count(total_candidates: int, batch_size: int, configured_batches: int) -> int:
    """Return the number of candidate pages to verify for this run."""
    if total_candidates <= 0:
        return 0
    return min(math.ceil(total_candidates / batch_size), configured_batches)


def resolve_task_result(value: Any) -> Any:
    """Resolve Prefect futures while leaving plain test doubles untouched."""
    return value.result() if hasattr(value, "result") else value


# Backwards-compatible private alias for existing callers/tests.
_resolve_task_result = resolve_task_result


def _accepts_settings_argument(callable_obj: Callable[..., Any], current_arg_count: int) -> bool:
    """Return False only when a test double clearly exposes a legacy fixed signature."""
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return True
    positional_capacity = 0
    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
        if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            positional_capacity += 1
    return positional_capacity > current_arg_count


def _call_candidate_count_task(config: Any, colin_extract_engine: Engine, settings: VerifyAuthSettings) -> Any:
    if _accepts_settings_argument(get_candidate_count_task, 2):
        return get_candidate_count_task(config, colin_extract_engine, settings)
    return get_candidate_count_task(config, colin_extract_engine)


def _call_candidate_page_task(
    config: Any,
    colin_extract_engine: Engine,
    limit: int,
    offset: int,
    settings: VerifyAuthSettings,
) -> Any:
    if _accepts_settings_argument(get_candidate_page_task, 4):
        return get_candidate_page_task(config, colin_extract_engine, limit, offset, settings)
    return get_candidate_page_task(config, colin_extract_engine, limit, offset)


def _call_expected_accounts_task(
    config: Any,
    colin_extract_engine: Engine,
    business_identifiers: list[str],
    settings: VerifyAuthSettings,
) -> Any:
    if _accepts_settings_argument(read_expected_accounts_task, 3):
        return read_expected_accounts_task(config, colin_extract_engine, business_identifiers, settings)
    return read_expected_accounts_task(config, colin_extract_engine, business_identifiers)


def _submit_verify_batch(
    config: Any,
    auth_engine: Engine,
    business_identifiers: list[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None,
    settings: VerifyAuthSettings,
) -> Any:
    """Submit one Auth verification/inspection task, with a sync fallback for non-Prefect tests."""
    args = (config, auth_engine, business_identifiers, expected_accounts_by_identifier, settings)
    legacy_args = (config, auth_engine, business_identifiers, expected_accounts_by_identifier)
    if hasattr(verify_auth_batch_task, "submit"):
        submit = verify_auth_batch_task.submit
        return submit(*args) if _accepts_settings_argument(submit, 4) else submit(*legacy_args)
    if _accepts_settings_argument(verify_auth_batch_task, 4):
        return verify_auth_batch_task(*args)
    return verify_auth_batch_task(*legacy_args)


@task(name="Count verify Auth candidates", cache_policy=NO_CACHE)
def get_candidate_count_task(
    config: Any,
    colin_extract_engine: Engine,
    settings: AuthCandidateSettings | None = None,
) -> int:
    """Prefect task wrapper for the aligned selected-candidate count query."""
    return get_candidate_count(config, colin_extract_engine, settings)


@task(name="Page verify Auth candidates", cache_policy=NO_CACHE)
def get_candidate_page_task(
    config: Any,
    colin_extract_engine: Engine,
    limit: int,
    offset: int,
    settings: AuthCandidateSettings | None = None,
) -> list[str]:
    """Prefect task wrapper for deterministic selected-candidate paging."""
    return get_candidate_page(config, colin_extract_engine, limit, offset, settings)


@task(name="Read verify Auth expected affiliation accounts", cache_policy=NO_CACHE)
def read_expected_accounts_task(
    config: Any,
    colin_extract_engine: Engine,
    business_identifiers: list[str],
    settings: AuthCandidateSettings | None = None,
) -> dict[str, tuple[str, ...]]:
    """Prefect task wrapper for read-only expected-account derivation."""
    return read_expected_accounts_for_candidates(config, colin_extract_engine, business_identifiers, settings)


@task(name="Verify Auth DB batch", cache_policy=NO_CACHE)
def verify_auth_batch_task(
    config: Any,
    auth_engine: Engine,
    business_identifiers: list[str],
    expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None,
    settings: AuthBatchSettings | None = None,
) -> AuthBatchResult:
    """Prefect task wrapper for one Auth DB read-back batch."""
    return run_auth_batch(config, auth_engine, business_identifiers, expected_accounts_by_identifier, settings)


def warn_if_affiliation_and_invite_selected(settings: VerifyAuthSettings) -> None:
    """Emit the valid-but-unusual affiliation+invite warning once from flow/entrypoint paths."""
    if settings.check_affiliation and CHECK_INVITE in settings.selected_checks:
        LOGGER.warning(AFFILIATION_INVITE_WARNING)


def format_console_limit(console_limit: ConsoleLimit) -> str:
    if console_limit.disabled:
        return "0"
    if console_limit.max_rows is None:
        return "ALL"
    return str(console_limit.max_rows)


# Backwards-compatible private alias for existing callers/tests.
_format_console_limit = format_console_limit


def _format_start_message(settings: VerifyAuthSettings) -> str:
    return (
        "👷 Verify Auth starting. "
        f"SelectionMode={settings.selection_mode.value}, "
        f"SelectedChecks={','.join(settings.selected_checks) or '(none)'}, "
        f"ConsoleLimit={format_console_limit(settings.console_limit)}, "
        f"ConfiguredBatches={settings.batches}, BatchSize={settings.batch_size}, "
        "RunnerAssumption=local/threaded"
    )


def _run_verify_auth_flow_with_engines(
    config: Any,
    settings: VerifyAuthSettings,
    colin_extract_engine: Engine,
    auth_engine: Engine,
) -> dict[str, int]:
    """Run verify-auth orchestration using already-initialized engines.

    This helper keeps the Prefect entrypoint thin and lets unit tests inject fake
    engines/task results without opening live database connections.
    """
    total_candidates = _call_candidate_count_task(config, colin_extract_engine, settings)
    total_candidates = int(resolve_task_result(total_candidates) or 0)
    batch_count = calculate_batch_count(total_candidates, settings.batch_size, settings.batches)
    print(
        "👷 Auth candidate selection ready. "
        f"TotalCandidates={total_candidates}, BatchCount={batch_count}, "
        f"SelectionMode={settings.selection_mode.value}, "
        f"AuthMigGroupIds={settings.auth_mig_group_ids or '(none)'}, "
        f"AuthMigBatchIds={settings.auth_mig_batch_ids or '(none)'}"
    )

    futures: list[Any] = []
    for batch_index in range(batch_count):
        offset = batch_index * settings.batch_size
        business_identifiers = _call_candidate_page_task(
            config,
            colin_extract_engine,
            settings.batch_size,
            offset,
            settings,
        )
        business_identifiers = [str(identifier) for identifier in (resolve_task_result(business_identifiers) or [])]

        expected_accounts_by_identifier: dict[str, Iterable[str]] | None = None
        if settings.read_expected_accounts:
            expected_accounts_by_identifier = _call_expected_accounts_task(
                config,
                colin_extract_engine,
                business_identifiers,
                settings,
            )
            expected_accounts_by_identifier = resolve_task_result(expected_accounts_by_identifier) or {}

        print(
            f"🚀 Submitting verify-auth batch {batch_index + 1}/{batch_count}: "
            f"offset={offset}, candidate_count={len(business_identifiers)}"
        )
        futures.append(
            _submit_verify_batch(
                config,
                auth_engine,
                business_identifiers,
                expected_accounts_by_identifier,
                settings,
            )
        )

    results: list[VerificationResult] = []
    for future in futures:
        batch_result = resolve_task_result(future)
        if isinstance(batch_result, AuthBatchResult):
            results.extend(batch_result.verification_results)
        else:
            # Backwards-compatible path for existing tests/doubles that return verification results directly.
            results.extend(batch_result or [])

    summary = build_summary_row(results, settings.selected_checks)
    scenario_rows = build_scenario_rows(results)
    print(
        "🌟 Verify Auth tasks complete. "
        f"TotalVerified={summary['total_count']}, Success={summary['success_count']}, "
        f"Failure={summary['failure_count']}, ScenarioBuckets={len(scenario_rows)}"
    )
    print_scenario_summary_rows(scenario_rows)
    print_scenario_rows(
        scenario_rows,
        console_limit=settings.console_limit,
        copy_list_path=settings.scenario_path,
        limit_config_key="VERIFY_AUTH_CONSOLE_LIMIT",
    )

    write_verification_reports(settings, results)
    print(
        "🌰 Verify Auth reports written. "
        f"SummaryPath={settings.summary_path}, DetailPath={settings.detail_path}, "
        f"ScenarioPath={settings.scenario_path}"
    )

    return summary


def dispose_engine(engine: Any) -> None:
    """Dispose a SQLAlchemy engine if the object supports disposal."""
    dispose = getattr(engine, "dispose", None)
    if callable(dispose):
        dispose()


# Backwards-compatible private alias for existing callers/tests.
_dispose_engine = dispose_engine


def _initialize_and_run_verify_auth_flow() -> dict[str, int]:
    """Validate config, initialize engines once, and run verify-auth orchestration."""
    from common.init_utils import auth_init, colin_extract_init, get_config

    config = get_config()
    settings = validate_config(config)
    print(_format_start_message(settings))
    LOGGER.info(LOCAL_THREADED_EXECUTION_ASSUMPTION)
    warn_if_affiliation_and_invite_selected(settings)

    # Build once before connecting so config/query validation happens as early as practical.
    build_candidate_queries(config, settings)

    colin_extract_engine = colin_extract_init(config)
    auth_engine = None
    try:
        auth_engine = auth_init(config)
        return _run_verify_auth_flow_with_engines(config, settings, colin_extract_engine, auth_engine)
    finally:
        dispose_engine(auth_engine)
        dispose_engine(colin_extract_engine)


@flow(name="Verify-Auth-Flow", log_prints=True)
def verify_auth_flow() -> dict[str, int]:
    """Validate config, verify selected Auth DB candidates, and write reports."""
    return _initialize_and_run_verify_auth_flow()


def _format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _format_tuple(values: Iterable[Any]) -> str:
    return ",".join(str(value) for value in values)


def _row_value(row: Any, index: int, *names: str) -> Any:
    if hasattr(row, "_mapping"):
        mapping = row._mapping
        for name in names:
            if name in mapping:
                return mapping[name]
        lowered = {str(key).lower(): value for key, value in mapping.items()}
        for name in names:
            lowered_name = name.lower()
            if lowered_name in lowered:
                return lowered[lowered_name]
    if isinstance(row, dict):
        for name in names:
            if name in row:
                return row[name]
    return row[index]


def _row_value_or_none(row: Any, index: int, *names: str) -> Any:
    try:
        return _row_value(row, index, *names)
    except (IndexError, KeyError):
        return None


if __name__ == "__main__":
    verify_auth_flow()
