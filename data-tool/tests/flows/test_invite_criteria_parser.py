from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

import pytest


FLOWS_PATH = Path(__file__).resolve().parents[2] / "flows"
sys.path.insert(0, str(FLOWS_PATH))

from auth import auth_report_helpers  # noqa: E402
from auth.verify_auth_flow import (  # noqa: E402
    AuthInviteDiagnostics,
    InviteClause,
    InviteClauseKind,
    evaluate_invite_clauses,
    format_invite_criteria,
    parse_invite_criteria,
)


NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
AGE_ALIAS_CASES = (
    ("all_ages", ">=", "newest_age>=30", True),
    ("all_ages", ">", "newest_age>30", False),
    ("all_ages", "<=", "age[1]<=30", True),
    ("all_ages", "<", "age[1]<30", False),
    ("any_age", ">=", "age[1]>=30", True),
    ("any_age", ">", "age[1]>30", False),
    ("any_age", "<=", "newest_age<=30", True),
    ("any_age", "<", "newest_age<30", False),
)
AGE_ALIAS_CASE_IDS = tuple(f"{alias}{operator}" for alias, operator, _canonical, _expected in AGE_ALIAS_CASES)


def _parse(raw, *, expiry_days=None):
    return parse_invite_criteria(raw, now=NOW, expiry_days=expiry_days)


def _results(raw, diagnostics, *, expiry_days=None):
    criteria = _parse(raw, expiry_days=expiry_days)
    assert criteria is not None
    return tuple(passed for _clause, passed in evaluate_invite_clauses(diagnostics, criteria))


def _age_diagnostics(*age_days, unknown_count=0):
    now = NOW.replace(tzinfo=None)
    return AuthInviteDiagnostics(
        unaffiliated_unclaimed_count=len(age_days) + unknown_count,
        unknown_age_unclaimed_unaffiliated_count=unknown_count,
        unaffiliated_unclaimed_sent_dates=tuple(now - timedelta(days=days) for days in age_days),
    )


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_blank_criteria_is_unset(raw):
    assert _parse(raw) is None


def test_parser_normalizes_case_whitespace_aliases_and_full_expression():
    criteria = _parse(" COUNT >= 3 , AGE[ 1 ] >= 90, Newest_Age > 30, All_Expired ", expiry_days=30)

    assert criteria is not None
    assert criteria.raw == "count>=3, age[1]>=90, newest_age>30, all_expired"
    assert criteria.now == datetime(2026, 7, 24, 12, 0)
    assert criteria.cutoff == datetime(2026, 6, 24, 12, 0)
    assert criteria.requires_expiry()
    assert criteria.has_age_clauses()
    assert [clause.op for clause in criteria.clauses] == ["GTE", "GTE", "GT", None]


def test_oldest_age_normalizes_to_the_same_clause_as_age_one():
    oldest = _parse("oldest_age>=90")
    positional = _parse("age[1]>=90")

    assert oldest is not None and positional is not None
    assert oldest.clauses == positional.clauses == (
        InviteClause(InviteClauseKind.AGE, "age[1]>=90", op="GTE", value=90, position=1),
    )


@pytest.mark.parametrize(
    "alias,operator,canonical,_boundary_expected",
    AGE_ALIAS_CASES,
    ids=AGE_ALIAS_CASE_IDS,
)
def test_explicit_age_aliases_normalize_to_canonical_endpoint_clauses(
    alias,
    operator,
    canonical,
    _boundary_expected,
):
    canonical_criteria = _parse(canonical)
    assert canonical_criteria is not None

    for raw in (f"{alias}{operator}30", f"  {alias.upper()}  {operator}  30  "):
        alias_criteria = _parse(raw)

        assert alias_criteria == canonical_criteria
        assert alias_criteria is not None
        assert alias_criteria.raw == canonical
        assert alias_criteria.clauses[0] == canonical_criteria.clauses[0]
        assert alias_criteria.clauses[0].raw == canonical


def test_explicit_age_aliases_preserve_expression_order_and_canonical_duplicates():
    criteria = _parse(
        "ALL_AGES >= 30, count>=1, any_age>=90, age[2]<60, all_expired, newest_age>=30",
        expiry_days=30,
    )

    assert criteria is not None
    assert criteria.raw == (
        "newest_age>=30, count>=1, age[1]>=90, age[2]<60, all_expired, newest_age>=30"
    )
    assert criteria.clauses[0] == criteria.clauses[-1]
    assert "all_ages" not in criteria.raw
    assert "any_age" not in criteria.raw
    rendered = format_invite_criteria(criteria)
    assert 'Criteria="newest_age>=30, count>=1, age[1]>=90, age[2]<60, all_expired, newest_age>=30"' in rendered
    assert "all_ages" not in rendered
    assert "any_age" not in rendered


def test_duplicate_clauses_are_preserved_and_longest_match_operators_are_used():
    criteria = _parse("count>=3, count>=3, age[2]<=60")

    assert criteria is not None
    assert criteria.clauses[0] == criteria.clauses[1]
    assert [clause.op for clause in criteria.clauses] == ["GTE", "GTE", "LTE"]


@pytest.mark.parametrize(
    "raw,fragment",
    [
        ("count=3", "clause 1 'count=3': unknown operator '='; expected one of == >= <= > <"),
        ("age[0]>=30", "clause 1 'age[0]>=30': position must be >= 1 (1 = oldest)"),
        ("age[1]==90", "clause 1 'age[1]==90': age clauses accept >= > <= < only"),
        (
            "count>=0",
            "clause 1 'count>=0': value must be a positive integer; use ENTITY_WITHOUT_INVITE for zero invites",
        ),
        (
            "all_expired>=1",
            "clause 1 'all_expired>=1': all_expired takes no operator or value",
        ),
        (
            "expired_all",
            "clause 1 'expired_all': unknown clause; expected count, all_expired, age[n], "
            "oldest_age, newest_age, all_ages, any_age",
        ),
        ("count>=2, , age[1]>30", "clause 2 '': must contain a clause between commas"),
    ],
)
def test_invalid_clauses_name_the_index_clause_and_reason(raw, fragment):
    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert "INSPECT_AUTH_INVITE_CRITERIA" in str(error.value)
    assert fragment in str(error.value)


def test_all_expired_requires_expiry_days_and_reports_its_actual_clause_index():
    with pytest.raises(ValueError) as error:
        _parse("count>=3, all_expired")

    assert "clause 2 'all_expired': all_expired requires INSPECT_AUTH_INVITE_EXPIRY_DAYS" in str(error.value)


def test_oversized_age_value_fails_during_parsing_with_clause_context():
    oversized = "9" * 30
    with pytest.raises(ValueError) as error:
        _parse(f"count>=1, age[1]>={oversized}")

    message = str(error.value)
    assert f"clause 2 'age[1]>={oversized}'" in message
    assert "outside the supported range for the reference clock" in message


@pytest.mark.parametrize("selector", ["all_ages", "any_age"])
def test_explicit_age_aliases_reject_equality(selector):
    raw = f"{selector}==30"

    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert f"clause 1 '{raw}': age clauses accept >= > <= < only" in str(error.value)


@pytest.mark.parametrize(
    "raw",
    [
        "all_ages>=0",
        "all_ages>=-1",
        "any_age<=0",
        "any_age<=-1",
    ],
)
def test_explicit_age_aliases_reject_nonpositive_thresholds(raw):
    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert f"clause 1 '{raw}': value must be a positive integer" in str(error.value)


@pytest.mark.parametrize(
    "raw",
    [
        "all_ages",
        "any_age",
        "all_ages=30",
        "any_age=30",
        "all_ages>=days",
        "any_age<days",
    ],
)
def test_malformed_explicit_age_aliases_use_the_age_selector_error(raw):
    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert (
        f"clause 1 '{raw}': expected an age selector followed by one of >= > <= < and a positive integer"
        in str(error.value)
    )


@pytest.mark.parametrize("raw", ["all_age>=30", "any_ages>=30", "every_age>=30"])
def test_unknown_age_quantifier_spellings_remain_unknown_clauses(raw):
    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert (
        f"clause 1 '{raw}': unknown clause; expected count, all_expired, age[n], oldest_age, "
        "newest_age, all_ages, any_age"
        in str(error.value)
    )


def test_malformed_explicit_age_alias_reports_its_actual_clause_index():
    with pytest.raises(ValueError) as error:
        _parse("count>=1, any_age=30")

    assert "clause 2 'any_age=30': expected an age selector" in str(error.value)


@pytest.mark.parametrize(
    "raw",
    ["age[*]>=30", "age[ * ]>=30", "age[]>=30", "age[**]>=30", "age[*]"],
)
def test_bare_age_wildcard_and_malformed_variants_remain_invalid(raw):
    with pytest.raises(ValueError) as error:
        _parse(raw)

    assert (
        f"clause 1 '{raw}': expected an age selector followed by one of >= > <= < and a positive integer"
        in str(error.value)
    )


@pytest.mark.parametrize(
    "alias,operator,canonical,_boundary_expected",
    AGE_ALIAS_CASES,
    ids=AGE_ALIAS_CASE_IDS,
)
def test_oversized_explicit_age_alias_threshold_reports_canonical_clause(
    alias,
    operator,
    canonical,
    _boundary_expected,
):
    oversized = "9" * 30
    canonical_prefix = canonical.removesuffix("30")

    with pytest.raises(ValueError) as error:
        _parse(f"count>=1, {alias}{operator}{oversized}")

    message = str(error.value)
    assert f"clause 2 '{canonical_prefix}{oversized}'" in message
    assert "outside the supported range for the reference clock" in message


def test_formatter_and_helper_exports_expose_the_normalized_model():
    criteria = _parse("count == 3, all_expired", expiry_days=30)

    assert criteria is not None
    assert format_invite_criteria(criteria) == (
        'Criteria="count==3, all_expired", Now=2026-07-24T12:00:00Z, '
        "ExpiryDays=30, Cutoff=2026-06-24T12:00:00Z"
    )
    assert auth_report_helpers.InviteClause is InviteClause
    assert auth_report_helpers.InviteClauseKind is InviteClauseKind
    assert auth_report_helpers.parse_invite_criteria is parse_invite_criteria
    assert auth_report_helpers.evaluate_invite_clauses is evaluate_invite_clauses


@pytest.mark.parametrize(
    "operator,actual,expected",
    [
        ("==", 3, True),
        ("==", 2, False),
        (">=", 3, True),
        (">=", 2, False),
        ("<=", 3, True),
        ("<=", 4, False),
        (">", 4, True),
        (">", 3, False),
        ("<", 2, True),
        ("<", 3, False),
    ],
)
def test_count_clause_operator_boundaries(operator, actual, expected):
    diagnostics = AuthInviteDiagnostics(unaffiliated_unclaimed_count=actual)
    assert _results(f"count{operator}3", diagnostics) == (expected,)


@pytest.mark.parametrize(
    "operator,expected",
    [(">=", True), (">", False), ("<=", True), ("<", False)],
)
def test_age_clause_timestamp_precision_at_exact_threshold(operator, expected):
    sent_date = NOW.replace(tzinfo=None) - timedelta(days=30)
    diagnostics = AuthInviteDiagnostics(
        unaffiliated_unclaimed_count=1,
        unaffiliated_unclaimed_sent_dates=(sent_date,),
    )

    assert _results(f"age[1]{operator}30", diagnostics) == (expected,)


@pytest.mark.parametrize(
    "alias,operator,canonical,boundary_expected",
    AGE_ALIAS_CASES,
    ids=AGE_ALIAS_CASE_IDS,
)
def test_explicit_age_aliases_match_canonical_endpoints_at_exact_boundaries(
    alias,
    operator,
    canonical,
    boundary_expected,
):
    diagnostics = _age_diagnostics(30, 30)
    alias_result = _results(f"{alias}{operator}30", diagnostics)
    canonical_result = _results(canonical, diagnostics)

    assert alias_result == canonical_result == (boundary_expected,)


@pytest.mark.parametrize(
    "diagnostics",
    [
        pytest.param(_age_diagnostics(100, 60, 31, -1), id="future-newest"),
        pytest.param(_age_diagnostics(30, 30), id="tied-endpoints"),
        pytest.param(_age_diagnostics(100, unknown_count=1), id="known-and-unknown"),
        pytest.param(_age_diagnostics(), id="empty"),
        pytest.param(_age_diagnostics(unknown_count=2), id="all-null"),
    ],
)
@pytest.mark.parametrize(
    "alias,operator,canonical,_boundary_expected",
    AGE_ALIAS_CASES,
    ids=AGE_ALIAS_CASE_IDS,
)
def test_explicit_age_alias_direct_evaluation_equals_canonical_endpoint_across_edge_states(
    diagnostics,
    alias,
    operator,
    canonical,
    _boundary_expected,
):
    assert _results(f"{alias}{operator}30", diagnostics) == _results(canonical, diagnostics)


def test_explicit_age_aliases_preserve_future_date_endpoint_semantics():
    diagnostics = _age_diagnostics(100, -1)

    assert _results("all_ages>=30, any_age>=30", diagnostics) == (False, True)


@pytest.mark.parametrize(
    "diagnostics",
    [
        pytest.param(_age_diagnostics(100, unknown_count=1), id="known-and-unknown"),
        pytest.param(_age_diagnostics(), id="empty"),
        pytest.param(_age_diagnostics(unknown_count=2), id="all-null"),
    ],
)
def test_explicit_age_aliases_preserve_global_null_poisoning_and_false_on_empty(diagnostics):
    assert _results("all_ages>=30, any_age>=30, all_ages<=90, any_age<=90", diagnostics) == (
        False,
        False,
        False,
        False,
    )


def test_positional_and_newest_age_clauses_use_oldest_first_dates():
    now = NOW.replace(tzinfo=None)
    diagnostics = AuthInviteDiagnostics(
        unaffiliated_unclaimed_count=4,
        unaffiliated_unclaimed_sent_dates=(
            now - timedelta(days=100),
            now - timedelta(days=60),
            now - timedelta(days=31),
            now + timedelta(days=1),
        ),
    )

    assert _results("age[1]>=90, age[3]>=30, newest_age>=1", diagnostics) == (True, True, False)
    assert _results("age[5]>=1", diagnostics) == (False,)


def test_unknown_age_poisons_age_clauses_but_not_count_clauses():
    diagnostics = AuthInviteDiagnostics(
        unaffiliated_unclaimed_count=2,
        unknown_age_unclaimed_unaffiliated_count=1,
        unaffiliated_unclaimed_sent_dates=(NOW.replace(tzinfo=None) - timedelta(days=90),),
    )

    assert _results("count==2, age[1]>=30, newest_age<999", diagnostics) == (True, False, False)


@pytest.mark.parametrize(
    "diagnostics,expected",
    [
        (
            AuthInviteDiagnostics(
                unaffiliated_unclaimed_count=2,
                expired_unclaimed_unaffiliated_count=2,
            ),
            True,
        ),
        (
            AuthInviteDiagnostics(
                unaffiliated_unclaimed_count=2,
                expired_unclaimed_unaffiliated_count=1,
            ),
            False,
        ),
        (
            AuthInviteDiagnostics(
                unaffiliated_unclaimed_count=2,
                expired_unclaimed_unaffiliated_count=2,
                unknown_age_unclaimed_unaffiliated_count=1,
            ),
            False,
        ),
        (AuthInviteDiagnostics(), False),
    ],
)
def test_all_expired_preserves_nonempty_strict_cutoff_diagnostics_semantics(diagnostics, expected):
    assert _results("all_expired", diagnostics, expiry_days=30) == (expected,)
