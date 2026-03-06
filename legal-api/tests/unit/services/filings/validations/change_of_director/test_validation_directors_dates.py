# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test Change of Director director date validations. See rules in change_of_directors.py."""

import copy
from http import HTTPStatus

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import CHANGE_OF_DIRECTORS, FILING_HEADER

from legal_api.models import Business
from legal_api.services import flags
from legal_api.services.filings import validate
from legal_api.services.filings.validations.change_of_directors import get_cod_date_bounds
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests.unit.services.filings.validations import lists_are_equal

NOW = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
FOUNDING_DATE = NOW - datedelta.YEAR
LAST_COD_DATE_SAME_AS_FOUNDING = FOUNDING_DATE
LAST_COD_DATE_AFTER_FOUNDING = FOUNDING_DATE + datedelta.MONTH


def common_setup_cod(identifier: str, actions, cessationDate=None, appointmentDate=None, last_cod_date=LAST_COD_DATE_SAME_AS_FOUNDING):
    """Set up the data for COD director date validation tests."""
    business = Business(
        identifier=identifier,
        last_ledger_timestamp=FOUNDING_DATE,
        founding_date=FOUNDING_DATE,
        last_cod_date=last_cod_date
    )

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = NOW.date().isoformat()
    f['filing']['header']['effectiveDate'] = NOW.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier

    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    cod["directors"][0]["actions"] = actions
    cod["directors"][0]["cessationDate"] = cessationDate
    cod["directors"][0]["appointmentDate"] = appointmentDate or FOUNDING_DATE.date().isoformat()
    cod["directors"][1]["appointmentDate"] = FOUNDING_DATE.date().isoformat()
    f['filing']['changeOfDirectors'] = cod

    return business, f


@pytest.mark.parametrize(
    "test_name, actions, cessation_date, last_cod_date, expected_code, expected_msg",
    [
        (
            "SUCCESS - ceased director with cessationDate set",
            ["ceased"],
            "2025-01-01",
            LAST_COD_DATE_SAME_AS_FOUNDING,
            None,
            None
        ),
        (
            "SUCCESS - director with multiple actions including ceased",
            ["nameChanged", "ceased"],
            "2025-01-01",
            LAST_COD_DATE_SAME_AS_FOUNDING,
            None,
            None
        ),
        (
            "SUCCESS - appointed director with null cessationDate set",
            ["appointed"],
            None,
            LAST_COD_DATE_SAME_AS_FOUNDING,
            None,
            None
        ),
        (
            "FAIL - unchanged director with cessationDate set",
            [],
            "2025-01-01",
            LAST_COD_DATE_SAME_AS_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Cessation date must only be provided for a ceased director.",
                    "path": "/filing/changeOfDirectors/directors/0/cessationDate"
                }
            ]
        ),
        (
            "FAIL - ceased director with future cessationDate",
            ["ceased"],
            "2025-12-31",  # future relative to NOW
            LAST_COD_DATE_SAME_AS_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Cessation date cannot be in the future.",
                    "path": "/filing/changeOfDirectors/directors/0/cessationDate"
                }
            ]
        ),
        (
            "FAIL - ceased director with cessationDate before earliest allowed date",
            ["ceased"],
            "2023-01-01",  # before founding_date = last_cod_date
            LAST_COD_DATE_SAME_AS_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Cessation date cannot be before the business founding date or the most recent Change of Directors filing.",
                    "path": "/filing/changeOfDirectors/directors/0/cessationDate"
                }
            ]
        ),
        (
            "FAIL - ceased director with cessationDate before last_cod_date",
            ["ceased"],
            (LAST_COD_DATE_AFTER_FOUNDING - datedelta.DAY).date().isoformat(),  # day before last_cod_date
            LAST_COD_DATE_AFTER_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Cessation date cannot be before the business founding date or the most recent Change of Directors filing.",
                    "path": "/filing/changeOfDirectors/directors/0/cessationDate"
                }
            ]
        ),
        (
            "SUCCESS - ceased director with cessationDate after last_cod_date",
            ["ceased"],
            (LAST_COD_DATE_AFTER_FOUNDING + datedelta.DAY).date().isoformat(),  # day after last_cod_date
            LAST_COD_DATE_AFTER_FOUNDING,
            None,
            None
        ),
    ]
)
def test_validate_cod_director_cessation_date(session, test_name, actions, cessation_date, last_cod_date, expected_code, expected_msg):
    """Validate that cessation dates are properly validated."""
    # setup
    business, f = common_setup_cod("CP7654321", actions, cessationDate=cessation_date, last_cod_date=last_cod_date)

    # perform test with freeze_time
    with freeze_time(NOW):
        err = validate(business, f)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    "test_name, actions, appointment_date, last_cod_date, expected_code, expected_msg",
    [
        (
            "SUCCESS - appointed director with valid appointmentDate",
            ["appointed"],
            "2024-01-01",
            LAST_COD_DATE_SAME_AS_FOUNDING,
            None,
            None
        ),
        (
            "SUCCESS - director not appointed, appointmentDate ignored",
            ["nameChanged"],
            "2025-01-01",
            LAST_COD_DATE_SAME_AS_FOUNDING,
            None,
            None
        ),
        (
            "FAIL - appointed director with future appointmentDate",
            ["appointed"],
            "2025-12-31",  # future relative to NOW
            LAST_COD_DATE_SAME_AS_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Appointment date cannot be in the future.",
                    "path": "/filing/changeOfDirectors/directors/0/appointmentDate"
                }
            ]
        ),
        (
            "FAIL - appointed director before earliest allowed date",
            ["appointed"],
            "2023-01-01",  # before founding_date = last_cod_date
            LAST_COD_DATE_SAME_AS_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Appointment date cannot be before the business founding date or the most recent Change of Directors filing.",
                    "path": "/filing/changeOfDirectors/directors/0/appointmentDate"
                }
            ]
        ),
        (
            "FAIL - appointed director with appointmentDate before last COD date",
            ["appointed"],
            (LAST_COD_DATE_AFTER_FOUNDING - datedelta.DAY).date().isoformat(),  # day before last_cod_date
            LAST_COD_DATE_AFTER_FOUNDING,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    "error": "Appointment date cannot be before the business founding date or the most recent Change of Directors filing.",
                    "path": "/filing/changeOfDirectors/directors/0/appointmentDate"
                }
            ]
        ),
        (
            "SUCCESS - appointed director after last COD date",
            ["appointed"],
            (LAST_COD_DATE_AFTER_FOUNDING + datedelta.DAY).date().isoformat(), # day after last_cod_date
            LAST_COD_DATE_AFTER_FOUNDING,
            None,
            None
        ),
        (
            "SUCCESS - appointed director on last COD date",
            ["appointed"],
            (LAST_COD_DATE_AFTER_FOUNDING).date().isoformat(),
            LAST_COD_DATE_AFTER_FOUNDING,
            None,
            None
        ),
    ]
)
def test_validate_cod_director_appointment_date(session, test_name, actions, appointment_date, last_cod_date, expected_code, expected_msg):
    """Validate that appointment dates for directors follow COD rules."""
    # setup
    business, f = common_setup_cod("CP7654321", actions, appointmentDate=appointment_date, last_cod_date=last_cod_date)

    # perform test with freeze_time
    with freeze_time(NOW):
        err = validate(business, f)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


def test_validate_cessation_date_before_last_cod_with_flag_on(session, mocker):
    """Assert that cessation date before last_cod_date but after founding passes when flag is on."""
    mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
    # Use a date between founding and last_cod_date
    between_date = (FOUNDING_DATE + datedelta.DAY).date().isoformat()
    business, f = common_setup_cod(
        "CP7654321",
        actions=["ceased"],
        cessationDate=between_date,
        last_cod_date=LAST_COD_DATE_AFTER_FOUNDING
    )

    with freeze_time(NOW):
        err = validate(business, f)

    assert err is None


def test_validate_cessation_date_before_founding_with_flag_on(session, mocker):
    """Assert that cessation date before founding_date still fails even when flag is on."""
    mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
    business, f = common_setup_cod(
        "CP7654321",
        actions=["ceased"],
        cessationDate="2023-01-01",  # before founding_date
        last_cod_date=LAST_COD_DATE_SAME_AS_FOUNDING
    )

    with freeze_time(NOW):
        err = validate(business, f)

    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, [
        {
            "error": "Cessation date cannot be before the business founding date "
                     "or the most recent Change of Directors filing.",
            "path": "/filing/changeOfDirectors/directors/0/cessationDate"
        }
    ])


def test_validate_appointment_date_before_last_cod_with_flag_on(session, mocker):
    """Assert that appointment date before last_cod_date but after founding passes when flag is on."""
    mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
    between_date = (FOUNDING_DATE + datedelta.DAY).date().isoformat()
    business, f = common_setup_cod(
        "CP7654321",
        actions=["appointed"],
        appointmentDate=between_date,
        last_cod_date=LAST_COD_DATE_AFTER_FOUNDING
    )

    with freeze_time(NOW):
        err = validate(business, f)

    assert err is None


def test_validate_appointment_date_before_founding_with_flag_on(session, mocker):
    """Assert that appointment date before founding_date still fails even when flag is on."""
    mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
    business, f = common_setup_cod(
        "CP7654321",
        actions=["appointed"],
        appointmentDate="2023-01-01",  # before founding_date
        last_cod_date=LAST_COD_DATE_SAME_AS_FOUNDING
    )

    with freeze_time(NOW):
        err = validate(business, f)

    assert err.code == HTTPStatus.BAD_REQUEST
    assert lists_are_equal(err.msg, [
        {
            "error": "Appointment date cannot be before the business founding date "
                     "or the most recent Change of Directors filing.",
            "path": "/filing/changeOfDirectors/directors/0/appointmentDate"
        }
    ])


class TestGetCodDateBounds:
    """Tests for get_cod_date_bounds."""

    def test_flag_off_no_last_cod_date(self, session, mocker):
        """Flag off, no last_cod_date -> returns founding_date."""
        mocker.patch.object(flags, 'is_on', return_value=False)
        business = Business(founding_date=FOUNDING_DATE, last_cod_date=None)

        with freeze_time(NOW):
            earliest, today = get_cod_date_bounds(business)
            expected = LegislationDatetime.as_legislation_timezone(FOUNDING_DATE).date()
            assert earliest == expected
            assert today == LegislationDatetime.datenow()

    def test_flag_off_with_last_cod_date(self, session, mocker):
        """Flag off, last_cod_date after founding -> returns last_cod_date."""
        mocker.patch.object(flags, 'is_on', return_value=False)
        business = Business(founding_date=FOUNDING_DATE, last_cod_date=LAST_COD_DATE_AFTER_FOUNDING)

        with freeze_time(NOW):
            earliest, _ = get_cod_date_bounds(business)

        expected = LegislationDatetime.as_legislation_timezone(LAST_COD_DATE_AFTER_FOUNDING).date()
        assert earliest == expected

    def test_flag_on_with_last_cod_date(self, session, mocker):
        """Flag on, last_cod_date after founding -> returns founding_date (ignores last_cod_date)."""
        mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
        business = Business(founding_date=FOUNDING_DATE, last_cod_date=LAST_COD_DATE_AFTER_FOUNDING)

        with freeze_time(NOW):
            earliest, _ = get_cod_date_bounds(business)

        expected = LegislationDatetime.as_legislation_timezone(FOUNDING_DATE).date()
        assert earliest == expected

    def test_flag_on_no_last_cod_date(self, session, mocker):
        """Flag on, no last_cod_date -> returns founding_date."""
        mocker.patch.object(flags, 'is_on', side_effect=lambda flag, **kwargs: flag == 'enable-backdated-cod')
        business = Business(founding_date=FOUNDING_DATE, last_cod_date=None)

        with freeze_time(NOW):
            earliest, _ = get_cod_date_bounds(business)

        expected = LegislationDatetime.as_legislation_timezone(FOUNDING_DATE).date()
        assert earliest == expected
