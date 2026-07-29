import csv
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


FLOWS_PATH = Path(__file__).resolve().parents[2] / "flows"
sys.path.insert(0, str(FLOWS_PATH))

from auth import auth_report_helpers  # noqa: E402
from auth.verify_auth_flow import (  # noqa: E402
    CHECK_INVITE,
    INSPECTION_FIELDNAMES,
    INSPECT_FILTER_ALL,
    INSPECTION_LEGEND_LINES,
    AuthBusinessState,
    AuthInviteDiagnostics,
    ConsoleLimit,
    _INVITE_READ_SQL,
    _AuthInviteAccumulator,
    _all_inspection_summary_metric_rows,
    _dated_invite_sort_key,
    _format_invite_dates,
    _format_invite_mix,
    _format_invite_summary,
    build_inspection_rows,
    build_inspection_summary,
    build_verification_results,
    print_inspection_rows,
    parse_invite_criteria,
    read_auth_states_for_candidates,
    run_auth_batch,
    write_inspection_report,
    write_inspection_summary_txt,
)


class _FakeResult:
    def __init__(self, rows, *, allow_fetchall=True):
        self._rows = rows
        self._allow_fetchall = allow_fetchall

    def __iter__(self):
        return iter(self._rows)

    def fetchall(self):
        assert self._allow_fetchall, "invitation reads must stream rather than materialize all rows"
        return self._rows


class _FakeConnection:
    def __init__(self, entity_rows, invite_rows):
        self.entity_rows = entity_rows
        self.invite_rows = invite_rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, _params):
        sql = str(statement)
        if "FROM entities" in sql:
            return _FakeResult(self.entity_rows)
        if "FROM affiliation_invitations" in sql:
            return _FakeResult(self.invite_rows, allow_fetchall=False)
        return _FakeResult([])


class _FakeEngine:
    def __init__(self, entity_rows, invite_rows):
        self.connection = _FakeConnection(entity_rows, invite_rows)

    def connect(self):
        return self.connection


def _diagnostic_engine(cutoff, *, positional_invite_rows=False):
    entity_rows = [
        {"id": 1, "business_identifier": "BC123", "business_name": "Alpha"},
        {"id": 2, "business_identifier": "BC123", "business_name": "Alpha Duplicate"},
    ]
    invite_rows = [
        {
            "id": 101,
            "entity_id": 1,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": cutoff - timedelta(days=2),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 102,
            "entity_id": 1,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "ACCEPTED",
            "sent_date": cutoff - timedelta(days=10),
            "accepted_date": cutoff + timedelta(days=1),
            "is_deleted": True,
            "affiliation_id": 99,
        },
        {
            "id": 103,
            "entity_id": 1,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "EXPIRED",
            "sent_date": cutoff - timedelta(days=20),
            "accepted_date": None,
            "is_deleted": True,
            "affiliation_id": None,
        },
        {
            "id": 201,
            "entity_id": 2,
            "type": "OTHER",
            "invitation_status_code": "PENDING",
            "sent_date": (cutoff + timedelta(days=2)).replace(tzinfo=None),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 202,
            "entity_id": 2,
            "type": None,
            "invitation_status_code": None,
            "sent_date": None,
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 203,
            "entity_id": 2,
            "type": " UNAFFILIATED_EMAIL ",
            "invitation_status_code": " PENDING ",
            "sent_date": cutoff.replace(tzinfo=None),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 204,
            "entity_id": 2,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": None,
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 205,
            "entity_id": 2,
            "type": "OTHER",
            "invitation_status_code": "ACCEPTED",
            "sent_date": cutoff - timedelta(days=5),
            "accepted_date": cutoff + timedelta(days=2),
            "is_deleted": False,
            "affiliation_id": 100,
        },
    ]
    if positional_invite_rows:
        invite_rows = [
            (
                row["id"],
                row["entity_id"],
                row["type"],
                row["invitation_status_code"],
                row["sent_date"],
                row["accepted_date"],
                row["is_deleted"],
                row["affiliation_id"],
            )
            for row in invite_rows
        ]
    return _FakeEngine(entity_rows, invite_rows)


def test_invitation_read_is_row_level_and_excludes_sensitive_columns():
    assert "COUNT(" not in _INVITE_READ_SQL
    assert "GROUP BY" not in _INVITE_READ_SQL
    assert "ORDER BY entity_id, id" in _INVITE_READ_SQL
    assert "recipient_email" not in _INVITE_READ_SQL
    assert "token" not in _INVITE_READ_SQL
    assert "additional_message" not in _INVITE_READ_SQL


def test_dated_invite_sort_key_uses_date_numeric_entity_and_invitation_id_tiebreaks():
    earlier = datetime(2026, 5, 24, 12)
    tied = datetime(2026, 5, 25, 12)
    dated_invites = [
        (tied, "10", 1),
        (tied, "2", 10),
        (earlier, "99", 99),
        (tied, "2", 2),
    ]

    assert sorted(dated_invites, key=_dated_invite_sort_key) == [
        (earlier, "99", 99),
        (tied, "2", 2),
        (tied, "2", 10),
        (tied, "10", 1),
    ]


@pytest.mark.parametrize("positional_invite_rows", [False, True])
def test_row_aggregation_merges_entities_and_preserves_invite_count(positional_invite_rows):
    cutoff = datetime(2026, 6, 23, 12, tzinfo=timezone.utc)

    state = read_auth_states_for_candidates(
        _diagnostic_engine(cutoff, positional_invite_rows=positional_invite_rows),
        ["BC123"],
        selected_checks=(CHECK_INVITE,),
        invite_cutoff=cutoff,
    )[0]

    diagnostics = state.invite_diagnostics
    assert state.entity_ids == ("1", "2")
    assert state.invite_count == diagnostics.total_count == 8
    assert diagnostics.deleted_count == 1
    assert diagnostics.claimed_count == 2
    assert diagnostics.unclaimed_count == 5
    assert diagnostics.type_counts == (("(blank)", 1), ("OTHER", 2), ("UNAFFILIATED_EMAIL", 4))
    assert diagnostics.status_counts == (("(blank)", 1), ("ACCEPTED", 2), ("PENDING", 4))
    assert diagnostics.unaffiliated_unclaimed_count == 3
    assert diagnostics.expired_unclaimed_unaffiliated_count == 1
    assert diagnostics.current_unclaimed_unaffiliated_count == 1
    assert diagnostics.unknown_age_unclaimed_unaffiliated_count == 1
    assert diagnostics.unaffiliated_unclaimed_sent_dates == (
        datetime(2026, 6, 21, 12),
        datetime(2026, 6, 23, 12),
    )
    assert diagnostics.unaffiliated_unclaimed_count == (
        len(diagnostics.unaffiliated_unclaimed_sent_dates)
        + diagnostics.unknown_age_unclaimed_unaffiliated_count
    )
    assert diagnostics.oldest_unclaimed_sent_date == datetime(2026, 6, 21, 12)
    assert diagnostics.newest_unclaimed_sent_date == datetime(2026, 6, 25, 12)
    assert diagnostics.latest_accepted_date == datetime(2026, 6, 25, 12)
    assert diagnostics.total_count == (
        diagnostics.claimed_count + diagnostics.deleted_count + diagnostics.unclaimed_count
    )


def test_accepted_deleted_invite_renders_as_claimed_with_acceptance_date():
    cutoff = datetime(2026, 6, 23, 12)
    accumulator = _AuthInviteAccumulator()
    accumulator.add_row(
        invite_type="UNAFFILIATED_EMAIL",
        invitation_status_code="ACCEPTED",
        sent_date=cutoff - timedelta(days=10),
        accepted_date=cutoff + timedelta(days=1),
        is_deleted=True,
        invite_cutoff=cutoff,
    )
    diagnostics = accumulator.freeze(cutoff_configured=True)
    row = build_inspection_rows(
        [
            AuthBusinessState(
                business_identifier="BC123",
                entity_ids=("1",),
                invite_count=1,
                invite_diagnostics=diagnostics,
            )
        ]
    )[0]

    assert diagnostics.unaffiliated_unclaimed_count == 0
    assert _format_invite_summary(row) == "uncl=0 q=0(exp=0,cur=0) clm=1 del=0"
    assert _format_invite_dates(row) == "a:06-24"


def test_ordered_qualifying_dates_are_business_wide_deterministic_and_exclude_non_qualifying_rows():
    reference = datetime(2026, 7, 24, 12, tzinfo=timezone.utc)
    entity_rows = [
        {"id": 10, "business_identifier": "BC123", "business_name": "Alpha"},
        {"id": 2, "business_identifier": "BC123", "business_name": "Alpha"},
    ]
    tied = reference - timedelta(days=60)
    invite_rows = [
        {
            "id": 99,
            "entity_id": 10,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": reference + timedelta(days=1),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 20,
            "entity_id": 10,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": tied,
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 30,
            "entity_id": 2,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": tied,
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 10,
            "entity_id": 10,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": reference - timedelta(days=90),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 40,
            "entity_id": 2,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": None,
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
        {
            "id": 50,
            "entity_id": 2,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "PENDING",
            "sent_date": reference - timedelta(days=120),
            "accepted_date": None,
            "is_deleted": True,
            "affiliation_id": None,
        },
        {
            "id": 60,
            "entity_id": 2,
            "type": "UNAFFILIATED_EMAIL",
            "invitation_status_code": "ACCEPTED",
            "sent_date": reference - timedelta(days=110),
            "accepted_date": reference - timedelta(days=100),
            "is_deleted": False,
            "affiliation_id": 1,
        },
        {
            "id": 70,
            "entity_id": 2,
            "type": "OTHER",
            "invitation_status_code": "PENDING",
            "sent_date": reference - timedelta(days=100),
            "accepted_date": None,
            "is_deleted": False,
            "affiliation_id": None,
        },
    ]

    def read(rows):
        return read_auth_states_for_candidates(
            _FakeEngine(entity_rows, rows),
            ["BC123"],
            selected_checks=(CHECK_INVITE,),
            invite_cutoff=reference - timedelta(days=30),
        )[0].invite_diagnostics

    expected_dates = (
        datetime(2026, 4, 25, 12),
        datetime(2026, 5, 25, 12),
        datetime(2026, 5, 25, 12),
        datetime(2026, 7, 25, 12),
    )
    diagnostics = read(invite_rows)
    reverse_diagnostics = read(list(reversed(invite_rows)))

    assert diagnostics.unaffiliated_unclaimed_sent_dates == expected_dates
    assert reverse_diagnostics.unaffiliated_unclaimed_sent_dates == expected_dates
    assert diagnostics.unaffiliated_unclaimed_count == 5
    assert diagnostics.unknown_age_unclaimed_unaffiliated_count == 1
    assert diagnostics.unaffiliated_unclaimed_count == (
        len(diagnostics.unaffiliated_unclaimed_sent_dates)
        + diagnostics.unknown_age_unclaimed_unaffiliated_count
    )


def test_run_auth_batch_threads_optional_cutoff_and_legacy_settings_remain_compatible():
    cutoff = datetime(2026, 6, 23, 12, tzinfo=timezone.utc)
    config = SimpleNamespace()
    settings_with_cutoff = SimpleNamespace(
        batch_size=10,
        auth_read_checks=(CHECK_INVITE,),
        selected_checks=(CHECK_INVITE,),
        run_verify=False,
        invite_cutoff=cutoff,
    )

    state = run_auth_batch(
        config,
        _diagnostic_engine(cutoff),
        ["BC123"],
        settings=settings_with_cutoff,
    ).states[0]
    assert state.invite_diagnostics.expired_unclaimed_unaffiliated_count == 1

    legacy_settings = SimpleNamespace(
        batch_size=10,
        auth_read_checks=(CHECK_INVITE,),
        selected_checks=(CHECK_INVITE,),
        run_verify=False,
    )
    state_without_cutoff = run_auth_batch(
        config,
        _diagnostic_engine(cutoff),
        ["BC123"],
        settings=legacy_settings,
    ).states[0]
    assert state_without_cutoff.invite_count == 8
    assert state_without_cutoff.invite_diagnostics.expired_unclaimed_unaffiliated_count is None
    assert state_without_cutoff.invite_diagnostics.current_unclaimed_unaffiliated_count is None


REPORT_NOW = datetime(2026, 7, 24, 12, tzinfo=timezone.utc)
REPORT_CRITERIA = parse_invite_criteria(
    "count==2, age[1]>=50",
    now=REPORT_NOW,
    expiry_days=None,
)
assert REPORT_CRITERIA is not None


def _output_states():
    with_cutoff = AuthBusinessState(
        business_identifier="BC123",
        entity_ids=("1",),
        invite_count=3,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=3,
            claimed_count=1,
            unclaimed_count=2,
            type_counts=(("OTHER", 1), ("UNAFFILIATED_EMAIL", 2)),
            status_counts=(("ACCEPTED", 1), ("PENDING", 2)),
            unaffiliated_unclaimed_count=2,
            expired_unclaimed_unaffiliated_count=2,
            current_unclaimed_unaffiliated_count=0,
            unaffiliated_unclaimed_sent_dates=(
                datetime(2026, 6, 1, 1, 2, 3, tzinfo=timezone.utc),
                datetime(2026, 6, 2, 2, 3, 4),
            ),
            oldest_unclaimed_sent_date=datetime(2026, 6, 1, 1, 2, 3, tzinfo=timezone.utc),
            newest_unclaimed_sent_date=datetime(2026, 6, 2, 2, 3, 4),
            latest_accepted_date=datetime(2026, 6, 3, 3, 4, 5),
        ),
    )
    without_cutoff = AuthBusinessState(
        business_identifier="BC456",
        entity_ids=("2",),
        invite_count=1,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=1,
            unclaimed_count=1,
            type_counts=(("UNAFFILIATED_EMAIL", 1),),
            status_counts=(("PENDING", 1),),
            unaffiliated_unclaimed_count=1,
            unaffiliated_unclaimed_sent_dates=(datetime(2026, 7, 20, 12),),
        ),
    )
    return [with_cutoff, without_cutoff]


def test_csv_rows_append_diagnostics_and_distinguish_blank_from_zero():
    expected_appended_fields = [
        "invite_claimed_count",
        "invite_unclaimed_count",
        "invite_deleted_count",
        "invite_type_counts",
        "invite_status_counts",
        "unaffiliated_unclaimed_invite_count",
        "unaffiliated_unclaimed_expired_count",
        "unaffiliated_unclaimed_current_count",
        "unaffiliated_unclaimed_unknown_age_count",
        "oldest_unclaimed_sent_date",
        "newest_unclaimed_sent_date",
        "latest_accepted_date",
        "unaffiliated_unclaimed_sent_dates",
        "unaffiliated_unclaimed_ages_days",
        "invite_criteria_pass",
        "invite_criteria_failed_clauses",
    ]
    assert INSPECTION_FIELDNAMES[-16:] == expected_appended_fields

    rows_without_criteria = build_inspection_rows(_output_states())
    assert rows_without_criteria[0]["unaffiliated_unclaimed_sent_dates"] == (
        "2026-06-01T01:02:03;2026-06-02T02:03:04"
    )
    assert rows_without_criteria[0]["unaffiliated_unclaimed_ages_days"] == ""
    assert rows_without_criteria[0]["invite_criteria_pass"] == ""
    assert rows_without_criteria[0]["invite_criteria_failed_clauses"] == ""

    with_cutoff, without_cutoff = build_inspection_rows(_output_states(), REPORT_CRITERIA)
    assert with_cutoff["invite_type_counts"] == "OTHER=1;UNAFFILIATED_EMAIL=2"
    assert with_cutoff["invite_status_counts"] == "ACCEPTED=1;PENDING=2"
    assert with_cutoff["unaffiliated_unclaimed_expired_count"] == 2
    assert with_cutoff["unaffiliated_unclaimed_current_count"] == 0
    assert with_cutoff["oldest_unclaimed_sent_date"] == "2026-06-01T01:02:03"
    assert with_cutoff["unaffiliated_unclaimed_sent_dates"] == (
        "2026-06-01T01:02:03;2026-06-02T02:03:04"
    )
    assert with_cutoff["unaffiliated_unclaimed_ages_days"] == "53;52"
    assert with_cutoff["invite_criteria_pass"] == "true"
    assert with_cutoff["invite_criteria_failed_clauses"] == ""
    assert without_cutoff["invite_criteria_pass"] == "false"
    assert without_cutoff["invite_criteria_failed_clauses"] == "count==2;age[1]>=50"
    assert without_cutoff["unaffiliated_unclaimed_expired_count"] == ""
    assert without_cutoff["unaffiliated_unclaimed_current_count"] == ""
    assert "recipient_email" not in with_cutoff
    assert "token" not in with_cutoff


def test_reference_now_populates_diagnostic_ages_and_shared_report_writer(tmp_path):
    future_state = AuthBusinessState(
        business_identifier="BCFUTURE",
        entity_ids=("1",),
        invite_count=1,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=1,
            unclaimed_count=1,
            unaffiliated_unclaimed_count=1,
            unaffiliated_unclaimed_sent_dates=(REPORT_NOW + timedelta(hours=1),),
        ),
    )
    null_only_state = AuthBusinessState(
        business_identifier="BCNULL",
        entity_ids=("2",),
        invite_count=1,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=1,
            unclaimed_count=1,
            unaffiliated_unclaimed_count=1,
            unknown_age_unclaimed_unaffiliated_count=1,
        ),
    )

    rows = build_inspection_rows(
        [future_state, null_only_state],
        reference_now=REPORT_NOW,
    )
    criteria_rows = build_inspection_rows(
        [future_state, null_only_state],
        parse_invite_criteria("count>=1", now=REPORT_NOW, expiry_days=None),
        reference_now=REPORT_NOW + timedelta(days=10),
    )

    assert [row["unaffiliated_unclaimed_ages_days"] for row in rows] == ["-1", ""]
    assert [row["unaffiliated_unclaimed_ages_days"] for row in rows] == [
        row["unaffiliated_unclaimed_ages_days"] for row in criteria_rows
    ]
    assert build_inspection_rows([future_state])[0]["unaffiliated_unclaimed_ages_days"] == ""

    report_path = tmp_path / "inspect.csv"
    write_inspection_report(
        str(report_path),
        [future_state],
        reference_now=REPORT_NOW,
    )
    with report_path.open(newline="", encoding="utf-8") as report_file:
        persisted_row = next(csv.DictReader(report_file))
    assert persisted_row["unaffiliated_unclaimed_ages_days"] == "-1"


def test_invite_summary_distinguishes_all_unclaimed_from_qualifying_subset():
    assert _format_invite_summary(
        {
            "invite_unclaimed_count": 5,
            "unaffiliated_unclaimed_invite_count": 3,
            "unaffiliated_unclaimed_expired_count": 1,
            "unaffiliated_unclaimed_current_count": 1,
            "unaffiliated_unclaimed_unknown_age_count": 1,
            "invite_claimed_count": 1,
            "invite_deleted_count": 0,
        }
    ) == "uncl=5 q=3(exp=1,cur=1,unk=1) clm=1 del=0"


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            {
                "oldest_unclaimed_sent_date": "2026-06-01T01:02:03",
                "newest_unclaimed_sent_date": "2026-06-02T02:03:04",
                "latest_accepted_date": "2026-06-03T03:04:05",
            },
            "s:06-01→06-02 a:06-03",
        ),
        (
            {
                "oldest_unclaimed_sent_date": "2026-06-01T01:02:03",
                "newest_unclaimed_sent_date": "2026-06-01T01:02:03",
            },
            "s:06-01",
        ),
        (
            {
                "oldest_unclaimed_sent_date": "2025-12-31T01:02:03",
                "newest_unclaimed_sent_date": "2026-01-01T02:03:04",
                "latest_accepted_date": "2026-01-02T03:04:05",
            },
            "s:2025-12-31→2026-01-01 a:2026-01-02",
        ),
        ({"latest_accepted_date": "2026-06-03T03:04:05"}, "a:06-03"),
        ({}, ""),
    ],
)
def test_format_invite_dates(row, expected):
    assert _format_invite_dates(row) == expected


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        (
            {
                "invite_type_counts": "(blank)=1;EMAIL=2;UNAFFILIATED_EMAIL=4",
                "invite_status_counts": "(blank)=1;ACCEPTED=2;PENDING=4",
            },
            "T:(b)=1,EM=2,UE=4 S:(b)=1,ACC=2,PEND=4",
        ),
        ({}, ""),
        ({"invite_type_counts": "Something_Long=3"}, "T:SOMET=3"),
        ({"invite_status_counts": "EXPIRED=2"}, "S:EXPD=2"),
    ],
)
def test_format_invite_mix_abbreviates_known_buckets_and_uses_stable_fallback(row, expected):
    assert _format_invite_mix(row) == expected


def test_age_alias_failed_clause_rows_use_canonical_endpoints_without_schema_changes():
    fieldnames_before = tuple(INSPECTION_FIELDNAMES)
    criteria = parse_invite_criteria(
        "all_ages>=30, any_age>=90",
        now=REPORT_NOW,
        expiry_days=None,
    )
    assert criteria is not None

    _with_cutoff, failing_state = _output_states()
    row = build_inspection_rows([failing_state], criteria)[0]

    assert row["invite_criteria_pass"] == "false"
    assert row["invite_criteria_failed_clauses"] == "newest_age>=30;age[1]>=90"
    assert "all_ages" not in str(row)
    assert "any_age" not in str(row)
    assert tuple(INSPECTION_FIELDNAMES) == fieldnames_before


def test_console_shortens_missing_entity_states_without_changing_report_rows(capsys):
    state = AuthBusinessState(business_identifier="BC000", entity_ids=())
    rows = build_inspection_rows([state])

    assert rows[0]["contact_state"] == "not_applicable_entity_missing"
    assert rows[0]["affiliation_state"] == "not_applicable_entity_missing"
    assert rows[0]["invite_state"] == "not_applicable_entity_missing"

    print_inspection_rows(rows, ConsoleLimit(max_rows=None))
    console_output = capsys.readouterr().out
    assert console_output.count("na_entity_missing") == 3
    assert "not_applicable_entity_missing" not in console_output


def test_console_row_column_is_leftmost_and_numbers_business_rows(capsys):
    rows = build_inspection_rows(_output_states())

    print_inspection_rows(rows, ConsoleLimit(max_rows=None))

    output_lines = capsys.readouterr().out.splitlines()
    header_line = next(line for line in output_lines if "business_names" in line)
    header_cells = [cell.strip() for cell in header_line.split(" | ")]
    assert header_cells == [
        "row",
        "identifier",
        "business_names",
        "entity",
        "contact",
        "affiliation",
        "invite",
        "invite_mix",
        "invite_summary",
        "invite_dates",
        "found_account_ids",
        "found_account_names",
    ]
    assert "business_identifier" not in header_line
    assert {
        "entity_state",
        "contact_state",
        "affiliation_state",
        "invite_state",
    }.isdisjoint(header_cells)
    business_lines = [line for line in output_lines if "BC123" in line or "BC456" in line]
    assert [line.split(" | ", maxsplit=1)[0].strip() for line in business_lines] == ["1", "2"]


def test_console_truncation_marker_has_blank_row_cell_and_keeps_separators(capsys):
    rows = build_inspection_rows(_output_states())

    print_inspection_rows(rows, ConsoleLimit(max_rows=1))

    output_lines = capsys.readouterr().out.splitlines()
    header_line = next(line for line in output_lines if "business_names" in line)
    header_cells = [cell.strip() for cell in header_line.split(" | ")]
    marker_index = next(
        index for index, line in enumerate(output_lines)
        if "⚠️ 1 MORE ROWS NOT SHOWN" in line
    )
    assert "-+-" in output_lines[marker_index - 1]
    assert output_lines[marker_index - 1] == output_lines[marker_index + 1]
    marker_cells = output_lines[marker_index].split(" | ")
    assert marker_cells[0].strip() == ""
    assert marker_cells[header_cells.index("invite_mix")].strip() == ""


def test_console_row_column_does_not_change_schema_or_inspection_row_dicts(capsys):
    fieldnames_before = tuple(INSPECTION_FIELDNAMES)
    rows = build_inspection_rows(_output_states())
    row_keys = [tuple(row.keys()) for row in rows]

    print_inspection_rows(rows, ConsoleLimit(max_rows=None))
    capsys.readouterr()

    assert tuple(INSPECTION_FIELDNAMES) == fieldnames_before
    assert INSPECTION_FIELDNAMES[0] == "business_identifier"
    assert "row" not in INSPECTION_FIELDNAMES
    assert "identifier" not in INSPECTION_FIELDNAMES
    assert [row["business_identifier"] for row in rows] == ["BC123", "BC456"]
    state_keys = {
        "entity_state",
        "contact_state",
        "affiliation_state",
        "invite_state",
    }
    assert state_keys.issubset(INSPECTION_FIELDNAMES)
    assert all(state_keys.issubset(row) for row in rows)
    assert all("row" not in row for row in rows)
    assert [tuple(row.keys()) for row in rows] == row_keys


def test_console_and_summary_outputs_include_compact_diagnostics(tmp_path, capsys):
    states = _output_states()
    rows = build_inspection_rows(states, REPORT_CRITERIA)

    print_inspection_rows(rows, ConsoleLimit(max_rows=1))
    console_output = capsys.readouterr().out
    assert "invite_mix" in console_output
    assert "invite_summary" in console_output
    assert "invite_dates" in console_output
    assert "T:OTHER=1,UE=2 S:ACC=1,PEND=2" in console_output
    assert "uncl=2 q=2(exp=2,cur=0) clm=1 del=0 ages=53,52d" in console_output
    assert "s:06-01→06-02 a:06-03" in console_output
    assert "showing 1 of 2 matched" in console_output
    assert all(console_output.count(line) == 1 for line in INSPECTION_LEGEND_LINES)
    assert "1 MORE ROWS NOT SHOWN" in console_output

    print_inspection_rows(rows, ConsoleLimit(max_rows=None))
    all_console_output = capsys.readouterr().out
    assert "showing 2 of 2 matched" in all_console_output
    assert all(all_console_output.count(line) == 1 for line in INSPECTION_LEGEND_LINES)

    summary = build_inspection_summary(states, states, INSPECT_FILTER_ALL)
    assert summary["has_unclaimed_invite_count"] == 2
    assert summary["has_claimed_invite_count"] == 1
    assert summary["has_unaffiliated_unclaimed_invite_count"] == 2
    assert summary["unclaimed_invite_rows_total"] == 3
    labels = [label for label, _value in _all_inspection_summary_metric_rows(summary)]
    assert "HasUnclaimedInvite" in labels
    assert "HasClaimedInvite" in labels
    assert "HasUnaffiliatedUnclaimedInvite" in labels
    assert "UnclaimedInviteRows(invites)" in labels

    summary_path = tmp_path / "summary.txt"
    write_inspection_summary_txt(str(summary_path), [], summary)
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "HasUnclaimedInvite" in summary_text
    assert "UnclaimedInviteRows(invites)" in summary_text


def test_console_legend_lines_are_self_identifying_and_printed_before_table(monkeypatch):
    printed_lines = []
    monkeypatch.setattr(
        "builtins.print",
        lambda *values, **_kwargs: printed_lines.append(" ".join(str(value) for value in values)),
    )

    rows = build_inspection_rows(_output_states())
    print_inspection_rows(rows, ConsoleLimit(max_rows=None))

    assert all(line.startswith("Legend invite_") for line in INSPECTION_LEGEND_LINES)
    assert all(len(line) <= 120 for line in INSPECTION_LEGEND_LINES)
    assert all("\n" not in line for line in INSPECTION_LEGEND_LINES)
    assert all("\n" not in line for line in printed_lines)
    assert all(printed_lines.count(line) == 1 for line in INSPECTION_LEGEND_LINES)

    title_index = next(index for index, line in enumerate(printed_lines) if line.startswith("🔎 Inspect Auth state"))
    legend_indices = [printed_lines.index(line) for line in INSPECTION_LEGEND_LINES]
    first_border_index = next(index for index, line in enumerate(printed_lines) if "─┼─" in line)
    assert title_index < legend_indices[0]
    assert legend_indices == list(range(legend_indices[0], legend_indices[0] + len(INSPECTION_LEGEND_LINES)))
    assert legend_indices[-1] < first_border_index

    legend_text = " ".join(INSPECTION_LEGEND_LINES)
    assert "q=qualifying UNAFFILIATED_EMAIL unclaimed" in legend_text
    assert "exp=sent<Cutoff" in legend_text
    assert "cur=sent>=Cutoff" in legend_text
    assert "unk=NULL sent_date" in legend_text
    assert "clm=accepted (Auth soft-deletes)" in legend_text
    assert "del=without acceptance" in legend_text
    assert "ages=days since sent, qualifying only" in legend_text
    assert "s:=unclaimed sent range (all types)" in legend_text
    assert "a:=latest accepted date" in legend_text
    assert "CSV: inspect-auth-inspection.csv" in legend_text
    assert "T:=types" in legend_text
    assert "EM=EMAIL UE=UNAFFILIATED_EMAIL" in legend_text
    assert "S:=raw Auth status(es)" in legend_text
    assert "deleted-w/o-acceptance excluded→del=" in legend_text
    assert "all non-deleted invite types" not in legend_text


def test_console_legend_is_absent_when_no_rows_or_console_preview_is_disabled(capsys):
    print_inspection_rows([], ConsoleLimit(max_rows=None))
    no_rows_output = capsys.readouterr().out
    assert all(line not in no_rows_output for line in INSPECTION_LEGEND_LINES)

    rows = build_inspection_rows(_output_states())
    print_inspection_rows(rows, ConsoleLimit(disabled=True, max_rows=0))
    disabled_output = capsys.readouterr().out
    assert disabled_output == ""
    assert all(line not in disabled_output for line in INSPECTION_LEGEND_LINES)


def test_console_business_names_default_uncapped_and_configured_cap_is_console_only(
    tmp_path,
    capsys,
):
    business_name = "Long Business Name " * 4
    account_name = "Long Account Name " * 3
    states = [
        AuthBusinessState(
            business_identifier="BC1234567",
            entity_ids=("1",),
            business_names=(business_name,),
            found_account_ids=("123",),
            found_account_names=(account_name,),
        ),
    ]
    rows = build_inspection_rows(states)

    assert rows[0]["business_names"] == business_name
    assert rows[0]["found_account_names"] == account_name

    print_inspection_rows(rows, ConsoleLimit(max_rows=None))
    uncapped_console = capsys.readouterr().out
    assert business_name in uncapped_console
    assert f"{account_name[:27]}…" in uncapped_console
    assert account_name not in uncapped_console

    print_inspection_rows(
        rows,
        ConsoleLimit(max_rows=None),
        business_names_max_length=18,
    )
    capped_console = capsys.readouterr().out
    assert f"{business_name[:17]}…" in capped_console
    assert business_name not in capped_console
    assert f"{account_name[:27]}…" in capped_console
    assert account_name not in capped_console

    assert rows[0]["business_names"] == business_name
    assert rows[0]["found_account_names"] == account_name

    report_path = tmp_path / "inspect.csv"
    write_inspection_report(str(report_path), states)
    with report_path.open(newline="", encoding="utf-8") as report_file:
        persisted_row = next(csv.DictReader(report_file))
    assert persisted_row["business_names"] == business_name
    assert persisted_row["found_account_names"] == account_name


def test_console_renders_full_invite_mix_without_changing_report_cells(capsys):
    row = build_inspection_rows(_output_states())[0]
    type_counts = row["invite_type_counts"]
    status_counts = row["invite_status_counts"]
    full_mix = _format_invite_mix(row)
    assert len(full_mix) > 28

    print_inspection_rows([row], ConsoleLimit(max_rows=None))

    console = capsys.readouterr().out
    assert full_mix in console
    assert f"{full_mix[:27]}…" not in console
    assert row["invite_type_counts"] == type_counts
    assert row["invite_status_counts"] == status_counts


def test_console_caps_ordered_age_preview_at_six_entries(capsys):
    sent_dates = tuple(
        REPORT_NOW.replace(tzinfo=None) - timedelta(days=age)
        for age in range(8, 0, -1)
    )
    state = AuthBusinessState(
        business_identifier="BC999",
        entity_ids=("9",),
        invite_count=8,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=8,
            unclaimed_count=8,
            unaffiliated_unclaimed_count=8,
            unaffiliated_unclaimed_sent_dates=sent_dates,
        ),
    )
    criteria = parse_invite_criteria("count>=1", now=REPORT_NOW, expiry_days=None)
    assert criteria is not None

    rows = build_inspection_rows([state], criteria)
    print_inspection_rows(rows, ConsoleLimit(max_rows=None))
    console = capsys.readouterr().out

    assert "ages=8,7,6,5,4,3d,+2" in console
    assert "recipient_email" not in str(rows)
    assert "token" not in str(rows)
    assert "additional_message" not in str(rows)


def test_helper_export_and_verify_classification_compatibility():
    assert auth_report_helpers.AuthInviteDiagnostics is AuthInviteDiagnostics

    legacy_state = AuthBusinessState(business_identifier="BC123", entity_ids=("1",), invite_count=1)
    result = build_verification_results([legacy_state], (CHECK_INVITE,))[0]
    assert result.invite_success is True
    assert result.invite_count == 1
    assert legacy_state.invite_diagnostics == AuthInviteDiagnostics()
