# Copyright © 2019 Province of British Columbia
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
"""Test Change of Director effective date validations. See rules in change_of_directors.py."""
import copy

import datedelta
from freezegun import freeze_time
import pytest
from registry_schemas.example_data import ANNUAL_REPORT, CHANGE_OF_DIRECTORS, FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings.validations.change_of_directors import validate_effective_date
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests.unit.models import factory_completed_filing


def common_setup(identifier: str, date_time: datetime):
    """Set up the data for COD tests."""
    founding_date = date_time - datedelta.YEAR
    filing_date = date_time - datedelta.DAY
    effective_date = as_effective_date(filing_date)

    business = Business(identifier=identifier,
                        founding_date=founding_date)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = filing_date.isoformat()
    f['filing']['header']['effectiveDate'] = effective_date.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier

    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    f['filing']['changeOfDirectors'] = cod

    return business, f


def test_effective_date_sanity_check(session):
    """Assert that a COD with a valid effective date passes validation."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_in_future(session):
    """Assert that the effective date of change cannot be in the future."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    # The effective date _cannot_ be in the future.
    tomorrow = datetime(2001, 8, 6, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(tomorrow)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert err

    # The effective date _can_ be today.
    today = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(today)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err

    # The effective date _can_ be in the past.
    yesterday = datetime(2001, 8, 4, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(yesterday)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_before_founding(session):
    """Assert that the effective date cannot be a date prior to their Incorporation Date."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    # The effective date _cannot_ be before their Incorporation Date.
    before = datetime(2000, 8, 4, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(before)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert err

    # The effective date _can_ be on their Incorporation Date.
    on = datetime(2000, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(on)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err

    # The effective date _can_ be after their Incorporation Date.
    after = datetime(2000, 8, 6, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(after)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err

@pytest.mark.skip(reason="Temporarily skip test while ignoring COD date comparison")
def test_validate_effective_date_not_before_other_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the effective date of change cannot be before a previous COD filing."""
    # setup
    identifier = 'CP1234567'
    founding_date = datetime(2000, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business = Business(identifier=identifier,
                        founding_date=founding_date)
    business.save()
    now = datetime(2020, 7, 30, 12, 0, 0, 0, tzinfo=timezone.utc)

    # create the previous COD filing
    filing_cod = copy.deepcopy(FILING_HEADER)
    filing_cod['filing']['header']['name'] = 'changeOfDirectors'
    filing_cod['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    filing_date = datetime(2010, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    factory_completed_filing(business=business,
                             data_dict=filing_cod,
                             filing_date=filing_date)

    # The effective date _cannot_ be before the previous COD.
    before = datetime(2010, 8, 4, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(before)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert err

    # The effective date _can_ be on the same date as the previous COD.
    on = datetime(2010, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(on)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert not err

    # The effective date _can_ be after the previous COD.
    after = datetime(2010, 8, 6, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(after)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert not err

@pytest.mark.skip(reason="Temporarily skip test while ignoring COD date comparison")
def test_validate_effective_date_not_before_other_AR_with_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the effective date of change cannot be before a previous AR filing."""
    # setup
    identifier = 'CP1234567'
    founding_date = datetime(2000, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business = Business(identifier=identifier,
                        founding_date=founding_date)
    business.save()
    now = datetime(2020, 7, 30, 12, 0, 0, 0, tzinfo=timezone.utc)

    # create the previous AR filing
    filing_ar = copy.deepcopy(ANNUAL_REPORT)
    filing_ar['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    filing_date = datetime(2010, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    factory_completed_filing(business=business,
                             data_dict=filing_ar,
                             filing_date=filing_date)

    # The effective date _cannot_ be before the previous AR.
    before = datetime(2010, 8, 4, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(before)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert err

    # The effective date _can_ be on the same date as the previous AR.
    on = datetime(2010, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(on)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert not err

    # The effective date _can_ be after the previous AR.
    after = datetime(2010, 8, 6, 12, 0, 0, 0, tzinfo=timezone.utc)
    effective_date = as_effective_date(after)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert not err


def as_effective_date(date_time: datetime) -> datetime:
    """Convert date_time to an effective date with 0 time in the legislation timezone, same as the UI does."""
    # 1. convert to legislation datetime
    # 2. zero out the time
    # 3. convert back to a UTC datetime
    date_time = LegislationDatetime.as_legislation_timezone(date_time)
    date_time = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return LegislationDatetime.as_utc_timezone(date_time)
