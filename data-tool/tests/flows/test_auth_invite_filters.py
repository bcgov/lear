from datetime import datetime, timedelta, timezone
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


FLOWS_PATH = Path(__file__).resolve().parents[2] / "flows"
CONFIG_PATH = FLOWS_PATH / "config.py"
sys.path.insert(0, str(FLOWS_PATH))

import auth.inspect_auth_flow as inspect_module  # noqa: E402
from auth import auth_report_helpers  # noqa: E402
from auth.auth_orchestration import normalize_auth_repeatable_cycle_key  # noqa: E402
from auth.inspect_auth_flow import (  # noqa: E402
    _format_start_message,
    _run_inspect_auth_flow_with_engines,
    parse_business_names_max_length,
    validate_inspect_config,
)
from auth.verify_auth_flow import (  # noqa: E402
    INSPECT_FILTER_ALL,
    INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION,
    INSPECT_FILTER_ENTITY_WITHOUT_CONTACT,
    INSPECT_FILTER_ENTITY_WITHOUT_INVITE,
    INSPECT_FILTER_HAS_AFFILIATION,
    INSPECT_FILTER_HAS_ANY_AUTH,
    INSPECT_FILTER_HAS_CONTACT,
    INSPECT_FILTER_HAS_ENTITY,
    INSPECT_FILTER_HAS_INVITE,
    INSPECT_FILTER_MISSING_ENTITY,
    INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA,
    AuthBatchResult,
    AuthBusinessState,
    AuthInviteDiagnostics,
    InviteCriteria,
    _AuthInviteAccumulator,
    _all_inspection_summary_metric_rows,
    _inspection_summary_metric_rows,
    auth_state_matches_inspect_filter,
    build_inspection_identifier_rows,
    build_inspection_rows,
    build_inspection_summary,
    filter_inspection_states,
    format_clock_minutes_z,
    format_clock_z,
    parse_inspect_filter,
    parse_invite_criteria,
    parse_invite_expiry_days,
    print_inspection_summary,
    write_inspection_summary_txt,
)


NEW_FILTER = INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA
NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
NOW_NAIVE = NOW.replace(tzinfo=None)
CUTOFF = NOW_NAIVE - timedelta(days=30)


def _criteria(raw="count>=1, all_expired", *, expiry_days=30):
    criteria = parse_invite_criteria(raw, now=NOW, expiry_days=expiry_days)
    assert criteria is not None
    return criteria


CRITERIA = _criteria()


def _config(tmp_path, **overrides):
    values = {
        "AUTH_REPORT_BATCHES": "1",
        "AUTH_REPORT_BATCH_SIZE": "10",
        "INSPECT_AUTH_FILTER": "ALL",
        "INSPECT_AUTH_CONSOLE_LIMIT": "0",
        "INSPECT_AUTH_INVITE_EXPIRY_DAYS": None,
        "INSPECT_AUTH_INVITE_CRITERIA": None,
        "AUTH_OUTPUT_PATH": str(tmp_path),
        "AUTH_SELECTION_MODE": "MANUAL",
        "AUTH_CORP_NUMS": "BC123,BC456",
        "AUTH_AFFILIATION_ACCOUNT_IDS_RAW": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _state(
    identifier="BC123",
    *,
    entity=True,
    affiliations=(),
    ages=(60,),
    unknown=0,
    qualifying=None,
    expired=None,
    current=None,
    claimed=0,
    deleted=0,
):
    sent_dates = tuple(sorted(NOW_NAIVE - timedelta(days=age) for age in ages))
    if qualifying is None:
        qualifying = len(sent_dates) + unknown
    if expired is None:
        expired = sum(sent_date < CUTOFF for sent_date in sent_dates)
    if current is None:
        current = len(sent_dates) - expired
    total = qualifying + claimed + deleted
    return AuthBusinessState(
        business_identifier=identifier,
        entity_ids=("1",) if entity else (),
        found_account_ids=tuple(affiliations),
        invite_count=total,
        invite_diagnostics=AuthInviteDiagnostics(
            total_count=total,
            deleted_count=deleted,
            claimed_count=claimed,
            unclaimed_count=qualifying,
            unaffiliated_unclaimed_count=qualifying,
            expired_unclaimed_unaffiliated_count=expired,
            current_unclaimed_unaffiliated_count=current,
            unknown_age_unclaimed_unaffiliated_count=unknown,
            unaffiliated_unclaimed_sent_dates=sent_dates,
        ),
    )


@pytest.mark.parametrize(
    "env_value,expected",
    [(None, "7"), ("", ""), ("   ", "   "), ("30", "30")],
)
def test_config_loading_distinguishes_missing_blank_and_override(monkeypatch, env_value, expected):
    if env_value is None:
        monkeypatch.delenv("INSPECT_AUTH_INVITE_EXPIRY_DAYS", raising=False)
    else:
        monkeypatch.setenv("INSPECT_AUTH_INVITE_EXPIRY_DAYS", env_value)

    spec = importlib.util.spec_from_file_location("expiry_config_boundary", CONFIG_PATH)
    assert spec is not None and spec.loader is not None
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    assert config_module._Config.INSPECT_AUTH_INVITE_EXPIRY_DAYS == expected


def test_config_loading_defaults_business_names_max_length_to_all(monkeypatch):
    monkeypatch.delenv("INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH", raising=False)

    spec = importlib.util.spec_from_file_location("business_names_config_boundary", CONFIG_PATH)
    assert spec is not None and spec.loader is not None
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    assert config_module._Config.INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH == "ALL"


@pytest.mark.parametrize(
    "raw,expected",
    [(None, None), ("", None), ("   ", None), ("ALL", None), ("all", None), ("12", 12), (1, 1)],
)
def test_parse_business_names_max_length_accepts_uncapped_and_positive_values(raw, expected):
    assert parse_business_names_max_length(raw) == expected


@pytest.mark.parametrize("raw", ["0", 0, "-1", -1, "not-a-length"])
def test_parse_business_names_max_length_rejects_non_positive_or_invalid_values(raw):
    with pytest.raises(
        ValueError,
        match="INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH must be a positive integer or ALL",
    ):
        parse_business_names_max_length(raw)


@pytest.mark.parametrize("raw", [None, "", "ALL"])
def test_inspect_settings_default_business_names_to_uncapped(tmp_path, raw):
    config = _config(tmp_path)
    if raw is not None:
        config.INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH = raw

    settings = validate_inspect_config(config)

    assert settings.business_names_max_length is None


def test_inspect_settings_apply_business_names_cap_and_reject_invalid_values(tmp_path):
    settings = validate_inspect_config(
        _config(tmp_path, INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH="31")
    )
    assert settings.business_names_max_length == 31

    invalid_config = _config(tmp_path, INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH="0")
    with pytest.raises(ValueError, match="INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH.*positive integer or ALL"):
        validate_inspect_config(invalid_config)


@pytest.mark.parametrize("raw,expected", [(None, 7), ("30", 30), (1, 1)])
def test_parse_invite_expiry_days_defaults_missing_and_accepts_positive_values(raw, expected):
    assert parse_invite_expiry_days(raw) == expected


@pytest.mark.parametrize("raw", ["", "   "])
def test_parse_invite_expiry_days_rejects_explicit_blank(raw):
    with pytest.raises(ValueError, match="must not be blank.*default of 7 days"):
        parse_invite_expiry_days(raw)


@pytest.mark.parametrize("raw", ["0", "-1", "abc"])
def test_parse_invite_expiry_days_rejects_non_positive_or_invalid(raw):
    with pytest.raises(ValueError, match="INSPECT_AUTH_INVITE_EXPIRY_DAYS.*positive integer.*use 1"):
        parse_invite_expiry_days(raw)


def test_new_filter_token_and_criteria_type_are_exported():
    assert parse_inspect_filter(NEW_FILTER.lower()) == NEW_FILTER
    assert auth_report_helpers.INSPECT_FILTER_NO_AFFILIATION_INVITE_CRITERIA == NEW_FILTER
    assert auth_report_helpers.InviteCriteria is InviteCriteria
    assert auth_report_helpers.format_clock_minutes_z is format_clock_minutes_z
    assert auth_report_helpers.format_clock_z is format_clock_z


def test_format_clock_minutes_z_truncates_display_without_changing_seconds_formatter():
    value = datetime(2026, 7, 24, 12, 34, 59, 987654, tzinfo=timezone.utc)

    assert format_clock_minutes_z(value) == "2026-07-24T12:34Z"
    assert format_clock_z(value) == "2026-07-24T12:34:59Z"
    assert format_clock_minutes_z(None) == ""


def test_validation_requires_nonblank_criteria_for_new_filter(tmp_path):
    config = _config(tmp_path, INSPECT_AUTH_FILTER=NEW_FILTER)

    with pytest.raises(ValueError, match="must contain at least one clause.*NO_AFFILIATION_INVITE_CRITERIA"):
        validate_inspect_config(config)


def test_validation_rejects_criteria_without_new_filter(tmp_path):
    config = _config(tmp_path, INSPECT_AUTH_INVITE_CRITERIA="count>=2")

    with pytest.raises(ValueError, match="INSPECT_AUTH_INVITE_CRITERIA only applies to.*NO_AFFILIATION"):
        validate_inspect_config(config)


def test_validation_uses_default_expiry_for_all_expired_clause(tmp_path):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_CRITERIA="count>=2, all_expired",
        )
    )
    assert settings.invite_expiry_days == 7
    assert settings.invite_criteria is not None
    assert settings.invite_criteria.cutoff == settings.invite_criteria.now - timedelta(days=7)


def test_validation_rejects_explicit_blank_expiry(tmp_path):
    config = _config(tmp_path, INSPECT_AUTH_INVITE_EXPIRY_DAYS="")

    with pytest.raises(ValueError, match="must not be blank.*default of 7 days"):
        validate_inspect_config(config)


def test_validation_defaults_missing_expiry_to_seven_day_diagnostics(tmp_path):
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    settings = validate_inspect_config(_config(tmp_path))
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert settings.invite_expiry_days == 7
    assert before.replace(microsecond=0) <= settings.run_clock <= after
    assert settings.run_clock.microsecond == 0
    assert settings.invite_cutoff == settings.run_clock - timedelta(days=7)
    assert settings.invite_cutoff.microsecond == 0
    assert before.replace(microsecond=0) - timedelta(days=7) <= settings.invite_cutoff <= after - timedelta(days=7)
    message = _format_start_message(settings)
    assert "ExpiryDays=7" in message
    assert "ExpiryRole=diagnostics-only" in message


def test_validation_rejects_oversized_expiry_before_database_work(tmp_path):
    config = _config(tmp_path, INSPECT_AUTH_INVITE_EXPIRY_DAYS="999999")

    with pytest.raises(ValueError, match="INSPECT_AUTH_INVITE_EXPIRY_DAYS.*supported range"):
        validate_inspect_config(config)


def test_validation_builds_criteria_with_one_shared_run_clock(tmp_path):
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_EXPIRY_DAYS="30",
            INSPECT_AUTH_INVITE_CRITERIA="count>=3, age[1]>=90, all_expired",
        )
    )
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    criteria = settings.invite_criteria
    assert criteria is not None
    assert criteria.raw == "count>=3, age[1]>=90, all_expired"
    assert before.replace(microsecond=0) <= criteria.now <= after
    assert criteria.now.microsecond == 0
    assert criteria.cutoff == criteria.now - timedelta(days=30)
    assert criteria.cutoff.microsecond == 0
    assert settings.run_clock == criteria.now
    assert settings.invite_cutoff is criteria.cutoff
    assert settings.invite_expiry_cutoff is criteria.cutoff


def test_validation_allows_expiry_only_as_diagnostics_with_standalone_cutoff(tmp_path):
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    settings = validate_inspect_config(
        _config(tmp_path, INSPECT_AUTH_INVITE_EXPIRY_DAYS="45")
    )
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert settings.inspect_filter == INSPECT_FILTER_ALL
    assert settings.invite_criteria is None
    assert before.replace(microsecond=0) <= settings.run_clock <= after
    assert settings.invite_cutoff == settings.run_clock - timedelta(days=45)
    assert before.replace(microsecond=0) - timedelta(days=45) <= settings.invite_cutoff <= after - timedelta(days=45)
    message = _format_start_message(settings)
    assert "ExpiryDays=45" in message
    assert "ExpiryRole=diagnostics-only" in message
    assert "Criteria=" not in message


def test_validation_allows_expiry_diagnostics_beside_non_expiry_criteria(tmp_path):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_EXPIRY_DAYS="30",
            INSPECT_AUTH_INVITE_CRITERIA="count>=3, newest_age>30",
        )
    )

    assert settings.invite_criteria is not None
    assert not settings.invite_criteria.requires_expiry()
    message = _format_start_message(settings)
    assert "CriteriaRole=filter" in message
    assert "ExpiryRole=diagnostics-only" in message


@pytest.mark.parametrize(
    "sent_date,expected_expired,expected_current,expected_unknown",
    [
        (CUTOFF - timedelta(seconds=1), 1, 0, 0),
        (CUTOFF, 0, 1, 0),
        (CUTOFF + timedelta(days=60), 0, 1, 0),
        (None, 0, 0, 1),
        ((CUTOFF - timedelta(days=1)).replace(tzinfo=timezone.utc), 1, 0, 0),
    ],
)
def test_temporal_buckets_use_strict_cutoff_and_normalize_awareness(
    sent_date, expected_expired, expected_current, expected_unknown
):
    accumulator = _AuthInviteAccumulator()
    accumulator.add_row(
        invite_type=" UNAFFILIATED_EMAIL ",
        invitation_status_code="PENDING",
        sent_date=sent_date,
        accepted_date=None,
        is_deleted=None,
        invite_cutoff=CUTOFF,
    )
    diagnostics = accumulator.freeze(cutoff_configured=True)
    assert diagnostics.expired_unclaimed_unaffiliated_count == expected_expired
    assert diagnostics.current_unclaimed_unaffiliated_count == expected_current
    assert diagnostics.unknown_age_unclaimed_unaffiliated_count == expected_unknown


@pytest.mark.parametrize(
    "criteria,state,expected",
    [
        (_criteria("count==3, all_expired"), _state(ages=(100, 60, 31)), True),
        (_criteria("count==3, all_expired"), _state(ages=(100, 60, 30)), False),
        (_criteria("count==3, age[1]>=90, age[3]>=30", expiry_days=None), _state(ages=(90, 60, 30)), True),
        (_criteria("count==3, age[1]>=90, age[3]>=30", expiry_days=None), _state(ages=(89, 60, 30)), False),
        (_criteria("count>=3, newest_age>30, age[1]>=90", expiry_days=None), _state(ages=(100, 70, 31, 40)), True),
        (_criteria("count>=3, newest_age>30, age[1]>=90", expiry_days=None), _state(ages=(100, 70, 30, 40)), False),
    ],
)
def test_required_operational_scenarios(criteria, state, expected):
    assert auth_state_matches_inspect_filter(state, NEW_FILTER, criteria) is expected


@pytest.mark.parametrize(
    "raw,ages,expected",
    [
        ("count==1, age[1]>=30", (30,), True),
        ("count==1, age[1]>=30", (29,), False),
        ("count==2, age[2]>=60", (90, 60), True),
        ("count==2, age[2]>=60", (90, 59), False),
        ("count==3, age[3]>=90", (120, 100, 90), True),
    ],
)
def test_reminder_cadence_criteria(raw, ages, expected):
    criteria = _criteria(raw, expiry_days=None)
    assert auth_state_matches_inspect_filter(_state(ages=ages), NEW_FILTER, criteria) is expected


@pytest.mark.parametrize(
    "changes",
    [
        {"entity": False},
        {"affiliations": ("10",)},
        {"ages": (), "qualifying": 0, "expired": 0, "current": 0},
    ],
)
def test_composite_predicate_requires_entity_no_affiliation_and_nonempty_q(changes):
    assert not auth_state_matches_inspect_filter(_state(**changes), NEW_FILTER, CRITERIA)


def test_accepted_deleted_invite_is_excluded_from_invite_criteria():
    accumulator = _AuthInviteAccumulator()
    accumulator.add_row(
        invite_type="UNAFFILIATED_EMAIL",
        invitation_status_code="ACCEPTED",
        sent_date=NOW_NAIVE - timedelta(days=60),
        accepted_date=NOW_NAIVE - timedelta(days=30),
        is_deleted=True,
        invite_cutoff=CUTOFF,
    )
    diagnostics = accumulator.freeze(cutoff_configured=True)
    state = AuthBusinessState(
        business_identifier="BC123",
        entity_ids=("1",),
        invite_count=diagnostics.total_count,
        invite_diagnostics=diagnostics,
    )

    assert diagnostics.claimed_count == 1
    assert diagnostics.deleted_count == 0
    assert diagnostics.unaffiliated_unclaimed_count == 0
    assert not auth_state_matches_inspect_filter(
        state,
        NEW_FILTER,
        _criteria("count>=1", expiry_days=None),
    )


def test_age_aliases_preserve_composite_base_predicates_and_nonempty_floor():
    criteria = _criteria("all_ages>=30", expiry_days=None)
    assert criteria.raw == "newest_age>=30"
    assert auth_state_matches_inspect_filter(_state(ages=(90, 30)), NEW_FILTER, criteria)
    assert not auth_state_matches_inspect_filter(
        _state(entity=False, ages=(90, 30)), NEW_FILTER, criteria
    )
    assert not auth_state_matches_inspect_filter(
        _state(affiliations=("10",), ages=(90, 30)), NEW_FILTER, criteria
    )
    assert not auth_state_matches_inspect_filter(
        _state(ages=(), qualifying=0, expired=0, current=0), NEW_FILTER, criteria
    )


def test_unknown_age_only_poisons_age_and_all_expired_clauses():
    count_only = _criteria("count==2", expiry_days=None)
    age_criteria = _criteria("count==2, age[1]>=30", expiry_days=None)
    state = _state(ages=(90,), unknown=1)

    assert auth_state_matches_inspect_filter(state, NEW_FILTER, count_only)
    assert not auth_state_matches_inspect_filter(state, NEW_FILTER, age_criteria)
    assert not auth_state_matches_inspect_filter(state, NEW_FILTER, CRITERIA)


def test_contradictory_criteria_match_nothing_without_validation_error():
    criteria = _criteria("count==3, count>=5", expiry_days=None)
    assert filter_inspection_states([_state(ages=(90, 60, 30))], NEW_FILTER, criteria) == []


@pytest.mark.parametrize(
    "operation,args_factory",
    [
        (auth_state_matches_inspect_filter, lambda: (_state(), NEW_FILTER)),
        (filter_inspection_states, lambda: ([], NEW_FILTER)),
        (build_inspection_identifier_rows, lambda: ([], [], NEW_FILTER)),
        (build_inspection_summary, lambda: ([], [], NEW_FILTER)),
    ],
)
def test_new_filter_without_criteria_always_raises_even_for_empty_batches(
    operation, args_factory
):
    args = args_factory()

    with pytest.raises(ValueError, match="INSPECT_AUTH_INVITE_CRITERIA"):
        operation(*args)


def test_preexisting_filters_are_unchanged_when_criteria_is_present():
    state = AuthBusinessState(
        business_identifier="BC123",
        entity_ids=("1",),
        usable_contact_count=1,
        found_account_ids=("10",),
        invite_count=1,
    )
    expected = {
        INSPECT_FILTER_ALL: True,
        INSPECT_FILTER_HAS_ANY_AUTH: True,
        INSPECT_FILTER_HAS_ENTITY: True,
        INSPECT_FILTER_MISSING_ENTITY: False,
        INSPECT_FILTER_HAS_CONTACT: True,
        INSPECT_FILTER_ENTITY_WITHOUT_CONTACT: False,
        INSPECT_FILTER_HAS_AFFILIATION: True,
        INSPECT_FILTER_ENTITY_WITHOUT_AFFILIATION: False,
        INSPECT_FILTER_HAS_INVITE: True,
        INSPECT_FILTER_ENTITY_WITHOUT_INVITE: False,
    }
    for filter_token, expected_match in expected.items():
        assert auth_state_matches_inspect_filter(state, filter_token) is expected_match
        assert auth_state_matches_inspect_filter(state, filter_token, CRITERIA) is expected_match


def test_identifier_metric_and_clause_audit_reporting(tmp_path, capsys):
    criteria = _criteria("count>=2, age[1]>=90", expiry_days=None)
    matching = _state("BC123", ages=(100, 40))
    count_miss = _state("BC456", ages=(100,))
    age_miss = _state("BC789", ages=(80, 40))
    states = [matching, count_miss, age_miss]

    rows_without = build_inspection_identifier_rows(states, states, INSPECT_FILTER_ALL)
    assert NEW_FILTER not in {row["inspect_filter"] for row in rows_without}
    summary_without = build_inspection_summary(states, states, INSPECT_FILTER_ALL)
    labels_without = {label for label, _value in _all_inspection_summary_metric_rows(summary_without)}
    assert "NoAffiliationInviteCriteria" not in labels_without

    matched = filter_inspection_states(states, NEW_FILTER, criteria)
    rows_with = build_inspection_identifier_rows(states, matched, INSPECT_FILTER_ALL, criteria)
    new_row = next(row for row in rows_with if row["inspect_filter"] == NEW_FILTER)
    assert new_row == {
        "inspect_filter": NEW_FILTER,
        "count": 1,
        "identifiers_csv": "BC123",
    }

    summary = build_inspection_summary(states, matched, INSPECT_FILTER_ALL, criteria)
    assert summary["no_affiliation_invite_criteria_count"] == 1
    assert summary["clause_audit"] == (("count>=2", 2), ("age[1]>=90", 2))
    affiliated = _state("BC000", ages=(100, 40), affiliations=("10",))
    affiliated_row = build_inspection_rows([affiliated], criteria)[0]
    assert affiliated_row["invite_criteria_pass"] == "true"
    assert affiliated_row["invite_criteria_failed_clauses"] == ""
    assert filter_inspection_states([affiliated], NEW_FILTER, criteria) == []
    assert "NoAffiliationInviteCriteria" in {
        label for label, _value in _all_inspection_summary_metric_rows(summary)
    }
    filtered_summary = build_inspection_summary(states, matched, NEW_FILTER, criteria)
    assert _inspection_summary_metric_rows(filtered_summary)[-1] == (
        "NoAffiliationInviteCriteria",
        1,
    )

    summary_path = tmp_path / "summary.txt"
    write_inspection_summary_txt(str(summary_path), rows_with, summary)
    summary_text = summary_path.read_text(encoding="utf-8")
    assert 'Criteria="count>=2, age[1]>=90", Now=2026-07-24T12:00:00Z' in summary_text
    assert "NoAffiliationInviteCriteria" in summary_text
    assert "# Invite criteria clause audit (businesses passing each clause, of 3 inspected)" in summary_text
    assert "count>=2" in summary_text
    assert "age[1]>=90" in summary_text

    print_inspection_summary(states, matched, INSPECT_FILTER_ALL, criteria)
    console = capsys.readouterr().out
    assert "Invite criteria clause audit" in console
    assert "of 3 inspected" in console


def test_age_aliases_are_canonical_in_settings_start_summary_audit_and_txt(tmp_path):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_CRITERIA="all_ages>=30, any_age>=90",
        )
    )
    criteria = settings.invite_criteria
    assert criteria is not None
    assert criteria.raw == "newest_age>=30, age[1]>=90"

    message = _format_start_message(settings)
    assert 'Criteria="newest_age>=30, age[1]>=90"' in message
    assert "all_ages" not in message
    assert "any_age" not in message

    matching = _state("BC123", ages=(100, 40))
    newest_miss = _state("BC456", ages=(100, 20))
    oldest_miss = _state("BC789", ages=(80, 40))
    states = [matching, newest_miss, oldest_miss]
    matched = filter_inspection_states(states, NEW_FILTER, criteria)
    assert matched == [matching]

    summary = build_inspection_summary(states, matched, NEW_FILTER, criteria)
    assert summary["invite_criteria"].startswith(
        'Criteria="newest_age>=30, age[1]>=90"'
    )
    assert summary["clause_audit"] == (("newest_age>=30", 2), ("age[1]>=90", 2))
    assert "all_ages" not in str(summary)
    assert "any_age" not in str(summary)

    summary_path = tmp_path / "alias-summary.txt"
    write_inspection_summary_txt(str(summary_path), [], summary)
    summary_text = summary_path.read_text(encoding="utf-8")
    assert 'Criteria="newest_age>=30, age[1]>=90"' in summary_text
    assert "newest_age>=30" in summary_text
    assert "age[1]>=90" in summary_text
    assert "all_ages" not in summary_text
    assert "any_age" not in summary_text


def test_summary_txt_writes_diagnostics_only_expiry_line(tmp_path):
    summary_path = tmp_path / "diagnostics-summary.txt"
    summary = {
        "inspect_filter": INSPECT_FILTER_ALL,
        "expiry_days": 45,
        "expiry_cutoff": datetime(2026, 6, 9, 12, 30, 0, 987654),
    }

    write_inspection_summary_txt(str(summary_path), [], summary)

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "ExpiryDays=45, Cutoff=2026-06-09T12:30:00Z (diagnostics-only)" in summary_text


def test_summary_txt_does_not_duplicate_expiry_line_when_criteria_is_present(tmp_path):
    summary_path = tmp_path / "criteria-summary.txt"
    summary = build_inspection_summary([], [], NEW_FILTER, CRITERIA)
    summary["expiry_days"] = 30
    summary["expiry_cutoff"] = CUTOFF

    write_inspection_summary_txt(str(summary_path), [], summary)

    summary_text = summary_path.read_text(encoding="utf-8")
    assert 'Criteria="count>=1, all_expired"' in summary_text
    assert "(diagnostics-only)" not in summary_text
    assert summary_text.count("ExpiryDays=30") == 1


def test_summary_txt_writes_nonempty_criteria_reminder_handoff(tmp_path):
    summary_path = tmp_path / "handoff-summary.txt"
    identifier_rows = [
        {
            "inspect_filter": NEW_FILTER,
            "count": 2,
            "identifiers_csv": "BC123,BC456",
        }
    ]

    write_inspection_summary_txt(
        str(summary_path),
        identifier_rows,
        handoff_filter=NEW_FILTER,
    )

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "# ── Next step: send reminder invites to this cohort" in summary_text
    assert "AUTH_SELECTION_MODE=MIGRATION_FILTER" in summary_text
    assert summary_text.count("AUTH_CORP_NUMS=BC123,BC456") == 2
    assert (
        "# REQUIRED: set a new key per reminder round, "
        "e.g. AUTH_REPEATABLE_CYCLE_KEY=saf_reminder_2"
    ) in summary_text
    cycle_key_line = next(
        line
        for line in summary_text.splitlines()
        if line.startswith("AUTH_REPEATABLE_CYCLE_KEY=")
    )
    assert cycle_key_line == "AUTH_REPEATABLE_CYCLE_KEY="
    emitted_cycle_key = cycle_key_line.partition("=")[2]
    config = SimpleNamespace(AUTH_REPEATABLE_CYCLE_KEY=emitted_cycle_key)
    with pytest.raises(ValueError, match="AUTH_REPEATABLE_CYCLE_KEY is required"):
        normalize_auth_repeatable_cycle_key(config)
    assert normalize_auth_repeatable_cycle_key(
        SimpleNamespace(AUTH_REPEATABLE_CYCLE_KEY="saf_reminder_2")
    ) == "saf_reminder_2"
    assert "AUTH_INVITE_IS_REMINDER=True" in summary_text
    assert "Auth stores no reminder ordinal" in summary_text


@pytest.mark.parametrize(
    "handoff_filter,count",
    [
        (None, 2),
        (INSPECT_FILTER_ALL, 2),
        (NEW_FILTER, 0),
    ],
)
def test_summary_txt_omits_handoff_outside_nonempty_criteria_cohort(
    tmp_path, handoff_filter, count
):
    summary_path = tmp_path / f"no-handoff-{handoff_filter}-{count}.txt"
    identifier_rows = [
        {
            "inspect_filter": NEW_FILTER,
            "count": count,
            "identifiers_csv": "BC123,BC456" if count else "",
        }
    ]

    write_inspection_summary_txt(
        str(summary_path),
        identifier_rows,
        handoff_filter=handoff_filter,
    )

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "Next step: send reminder invites" not in summary_text
    assert "AUTH_SELECTION_MODE=MIGRATION_FILTER" not in summary_text
    assert "AUTH_REPEATABLE_CYCLE_KEY=" not in summary_text
    assert "AUTH_INVITE_IS_REMINDER=True" not in summary_text


def test_start_message_reports_filter_expiry_and_normative_time_semantics(tmp_path):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_EXPIRY_DAYS="30",
            INSPECT_AUTH_INVITE_CRITERIA="count==2, all_expired, age[1]>=90",
        )
    )
    message = _format_start_message(settings)
    assert 'Criteria="count==2, all_expired, age[1]>=90"' in message
    assert "CriteriaRole=filter" in message
    assert "ExpiryRole=filter-clause" in message
    assert "AgeRule=timestamp-precision vs Now" in message
    assert "PositionRule=1=oldest" in message
    assert "NULL sent_date fails age clauses and all_expired" in message
    assert "CutoffClock=UTC once-per-run" in message


def test_inspect_integration_threads_same_criteria_to_batches_rows_reports_and_summary(
    tmp_path, monkeypatch, capsys
):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_CRITERIA="count>=1, all_ages>=30",
            INSPECT_AUTH_BUSINESS_NAMES_MAX_LENGTH="37",
        )
    )
    matching = _state("BC123", ages=(40,))
    nonmatching = _state("BC456", ages=(10,))
    captured = {}

    monkeypatch.setattr(inspect_module, "get_inspect_candidate_count_task", lambda *_args: 2)
    monkeypatch.setattr(
        inspect_module,
        "get_inspect_candidate_page_task",
        lambda *_args: ["BC123", "BC456"],
    )

    def fake_submit(_config_value, _engine, identifiers, _expected, submitted_settings):
        captured["identifiers"] = identifiers
        captured["batch_criteria"] = submitted_settings.invite_criteria
        captured["cutoff"] = submitted_settings.invite_cutoff
        return AuthBatchResult(states=[matching, nonmatching], verification_results=[])

    real_build_rows = build_inspection_rows

    def capture_rows(states, criteria, *, reference_now=None):
        captured["rows_criteria"] = criteria
        captured["rows_reference_now"] = reference_now
        return real_build_rows(states, criteria, reference_now=reference_now)

    monkeypatch.setattr(inspect_module, "_submit_inspect_batch", fake_submit)
    monkeypatch.setattr(inspect_module, "build_inspection_rows", capture_rows)
    monkeypatch.setattr(inspect_module, "print_inspection_summary", lambda *_args: None)
    monkeypatch.setattr(
        inspect_module,
        "print_inspection_rows",
        lambda *_args, **kwargs: captured.update(print_rows_kwargs=kwargs),
    )
    monkeypatch.setattr(inspect_module, "print_inspection_identifier_rows", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        inspect_module,
        "write_inspection_report",
        lambda _path, states, criteria, *, reference_now=None: captured.update(
            report_states=states,
            report_criteria=criteria,
            report_reference_now=reference_now,
        ),
    )
    monkeypatch.setattr(
        inspect_module,
        "write_inspection_summary_txt",
        lambda _path, rows, summary, *, handoff_filter=None: captured.update(
            identifier_rows=rows,
            summary=summary,
            handoff_filter=handoff_filter,
        ),
    )

    summary = _run_inspect_auth_flow_with_engines(
        SimpleNamespace(), settings, object(), object()
    )

    assert captured["identifiers"] == ["BC123", "BC456"]
    assert captured["batch_criteria"] is settings.invite_criteria
    assert captured["rows_criteria"] is settings.invite_criteria
    assert captured["rows_reference_now"] is settings.run_clock
    assert captured["print_rows_kwargs"]["business_names_max_length"] == 37
    assert captured["report_criteria"] is settings.invite_criteria
    assert captured["report_reference_now"] is settings.run_clock
    assert captured["cutoff"] is settings.invite_cutoff
    assert settings.invite_expiry_days == 7
    assert captured["report_states"] == [matching]
    assert captured["summary"] is summary
    assert captured["handoff_filter"] == NEW_FILTER
    assert summary["expiry_days"] == settings.invite_expiry_days
    assert summary["expiry_cutoff"] is settings.invite_cutoff
    assert summary["inspected_count"] == 2
    assert summary["matched_count"] == 1
    assert summary["no_affiliation_invite_criteria_count"] == 1
    assert settings.invite_criteria.raw == "count>=1, newest_age>=30"
    assert summary["clause_audit"] == (("count>=1", 2), ("newest_age>=30", 1))
    assert "all_ages" not in str(summary)
    assert captured["identifier_rows"] == [
        {"inspect_filter": NEW_FILTER, "count": 1, "identifiers_csv": "BC123"}
    ]
    console = capsys.readouterr().out
    clock_line = (
        f"🕐 Invite clock: Now={format_clock_minutes_z(settings.run_clock)}  "
        f"Cutoff={format_clock_minutes_z(settings.invite_cutoff)}  "
        f"ExpiryDays={settings.invite_expiry_days}  "
        "(expired means sent_date < Cutoff; one clock per run)"
    )
    assert clock_line in console
    assert format_clock_minutes_z(settings.run_clock).count(":") == 1
    assert format_clock_minutes_z(settings.invite_cutoff).count(":") == 1
    assert format_clock_z(settings.run_clock).count(":") == 2
    assert format_clock_z(settings.invite_cutoff).count(":") == 2
    assert (
        f"➡️  Reminder handoff block written to {settings.summary_path} — "
        "set a new AUTH_REPEATABLE_CYCLE_KEY before running make run-auth-invite."
    ) in console


def test_inspect_diagnostics_only_prints_clock_and_writes_expiry_without_handoff(
    tmp_path, monkeypatch, capsys
):
    settings = validate_inspect_config(
        _config(tmp_path, INSPECT_AUTH_INVITE_EXPIRY_DAYS="45")
    )
    monkeypatch.setattr(inspect_module, "get_inspect_candidate_count_task", lambda *_args: 0)

    summary = _run_inspect_auth_flow_with_engines(
        SimpleNamespace(), settings, object(), object()
    )

    console = capsys.readouterr().out
    clock_line = (
        f"🕐 Invite clock: Now={format_clock_minutes_z(settings.run_clock)}  "
        f"Cutoff={format_clock_minutes_z(settings.invite_cutoff)}  ExpiryDays=45  "
        "(expired means sent_date < Cutoff; one clock per run)"
    )
    assert clock_line in console
    assert format_clock_minutes_z(settings.run_clock).count(":") == 1
    assert format_clock_minutes_z(settings.invite_cutoff).count(":") == 1
    assert format_clock_z(settings.run_clock).count(":") == 2
    assert format_clock_z(settings.invite_cutoff).count(":") == 2
    assert "Reminder handoff block written" not in console
    summary_text = Path(settings.summary_path).read_text(encoding="utf-8")
    assert (
        f"ExpiryDays=45, Cutoff={format_clock_z(settings.invite_cutoff)} "
        "(diagnostics-only)"
    ) in summary_text
    assert "Next step: send reminder invites" not in summary_text
    assert summary["expiry_days"] == 45
    assert summary["expiry_cutoff"] is settings.invite_cutoff


def test_inspect_batch_failure_still_prevents_partial_report_writes(tmp_path, monkeypatch):
    settings = validate_inspect_config(
        _config(
            tmp_path,
            INSPECT_AUTH_FILTER=NEW_FILTER,
            INSPECT_AUTH_INVITE_CRITERIA="count>=1",
        )
    )
    writes = []
    monkeypatch.setattr(inspect_module, "get_inspect_candidate_count_task", lambda *_args: 1)
    monkeypatch.setattr(
        inspect_module,
        "get_inspect_candidate_page_task",
        lambda *_args: ["BC123"],
    )
    monkeypatch.setattr(
        inspect_module,
        "_submit_inspect_batch",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("batch failed")),
    )
    monkeypatch.setattr(
        inspect_module,
        "write_inspection_report",
        lambda *_args: writes.append("inspection"),
    )
    monkeypatch.setattr(
        inspect_module,
        "write_inspection_summary_txt",
        lambda *_args: writes.append("summary"),
    )

    config = SimpleNamespace()
    legal_engine = object()
    auth_engine = object()
    with pytest.raises(RuntimeError, match="batch failed"):
        _run_inspect_auth_flow_with_engines(config, settings, legal_engine, auth_engine)
    assert writes == []
