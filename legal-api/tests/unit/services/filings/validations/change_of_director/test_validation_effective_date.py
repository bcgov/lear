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
"""Test Change of Director basic validations. See rules in change_of_directors.py."""
import copy

import datedelta
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT, CHANGE_OF_DIRECTORS, FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings.validations.change_of_directors import validate_effective_date
from legal_api.utils.datetime import datetime, timezone
from tests.unit.models import factory_completed_filing


def common_setup(identifier: str, now: datetime):
    """Set up the data for COD tests."""
    founding_date = now - datedelta.YEAR
    filing_date = now - datedelta.DAY

    # create business founded "a year ago"
    business = Business(identifier=identifier,
                        founding_date=founding_date)

    # create COD filing filed (and effective) "yesterday"
    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = filing_date.isoformat()
    f['filing']['header']['effectiveDate'] = filing_date.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier

    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    f['filing']['changeOfDirectors'] = cod

    return business, f


def test_effective_date_sanity_check(session):
    """Assert that a COD with a valid effective date passes validation."""
    # setup
    identifier = 'CP1234567'
    # assign 'now' with non-zero hour so Founding Date is mid-day
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_in_future(session):
    """Assert that the effective date of change cannot be in the future."""
    # setup
    identifier = 'CP1234567'
    # assign 'now' with non-zero hour so Founding Date is mid-day
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    # The effective date _cannot_ be in the future.
    effective_date = datetime(2001, 8, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert err

    # The effective date _can_ be today.
    effective_date = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err

    # The effective date _can_ be in the past.
    effective_date = datetime(2001, 8, 4, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_before_founding(session):
    """Assert that the effective date cannot be a date prior to their Incorporation Date."""
    # setup
    identifier = 'CP1234567'
    # assign 'now' with non-zero hour so Founding Date is mid-day
    now = datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business, filing = common_setup(identifier, now)

    # The effective date _cannot_ be before their Incorporation Date.
    effective_date = datetime(2000, 8, 4, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert err

    # The effective date _can_ be on their Incorporation Date.
    effective_date = datetime(2000, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err

    # The effective date _can_ be after their Incorporation Date.
    effective_date = datetime(2000, 8, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_before_other_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the effective date of change cannot be before a previous COD filing."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2020, 7, 30, 12, 0, 0, 0, tzinfo=timezone.utc)
    # assign Founding Date with mid-day hour
    founding_date = datetime(2000, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business = Business(identifier=identifier,
                        founding_date=founding_date)
    business.save()

    # create the previous COD filing
    filing_cod = copy.deepcopy(FILING_HEADER)
    filing_cod['filing']['header']['name'] = 'changeOfDirectors'
    filing_cod['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    filing_date = datetime(2010, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    factory_completed_filing(business=business,
                             data_dict=filing_cod,
                             filing_date=filing_date)

    # The effective date _cannot_ be before the previous COD.
    effective_date = datetime(2010, 8, 4, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert err

    # The effective date _can_ be on the same date as the previous COD.
    effective_date = datetime(2010, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert not err

    # The effective date _can_ be after the previous COD.
    effective_date = datetime(2010, 8, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_cod['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert not err


def test_validate_effective_date_not_before_other_AR_with_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the effective date of change cannot be before a previous AR filing."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2020, 7, 30, 12, 0, 0, 0, tzinfo=timezone.utc)
    # assign founding_date with mid-day hour
    founding_date = datetime(2000, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc)
    business = Business(identifier=identifier,
                        founding_date=founding_date)
    business.save()

    # create the previous AR filing
    filing_ar = copy.deepcopy(ANNUAL_REPORT)
    filing_ar['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)
    filing_date = datetime(2010, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    factory_completed_filing(business=business,
                             data_dict=filing_ar,
                             filing_date=filing_date)

    # The effective date _cannot_ be before the previous AR.
    effective_date = datetime(2010, 8, 4, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert err

    # The effective date _can_ be on the same date as the previous AR.
    effective_date = datetime(2010, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert not err

    # The effective date _can_ be after the previous AR.
    effective_date = datetime(2010, 8, 6, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_ar['filing']['header']['effectiveDate'] = effective_date.isoformat()
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert not err
