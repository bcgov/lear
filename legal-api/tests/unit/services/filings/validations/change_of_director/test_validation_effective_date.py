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
"""Test Change of Director basic validations.

Rules: (text from the BA rules document)
    - The effective date of change cannot be in the future.
    - The effective date cannot be a date prior to their Incorporation Date
    - The effective date of change cannot be a date that is farther in the past
        as a previous COD filing(Standalone or AR).
    - The effective date can be the same effective date as another COD filing(standalone OR AR). If this is the case:
    - COD filing that was filed most recently as the most current director information.
"""
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
    filing_date = now - datedelta.DAY

    business = Business(identifier=identifier,
                        founding_date=now - datedelta.YEAR)

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
    now = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['effectiveDate'] = (now - datedelta.MONTH).isoformat()
    filing_json['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)

    business = Business(identifier=identifier,
                        founding_date=now - datedelta.datedelta(years=4)
                        )
    business.save()

    # create a COD
    factory_completed_filing(business=business,
                             data_dict=filing_json,
                             filing_date=(now - datedelta.MONTH))

    # move the COD to now
    filing_json['filing']['header']['effectiveDate'] = now.isoformat()

    with freeze_time(now):
        err = validate_effective_date(business, filing_json)
    assert not err


def test_validate_effective_date_not_in_future(session):
    """Assert that the effective date of change cannot be in the future."""
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)

    business, filing = common_setup(identifier, now)

    # The effective date of change cannot be in the future
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_before_founding(session):
    """Assert the filing is not before the business was founded.

    Rules:
        - The effective date cannot be a date prior to their Incorporation Date
    """
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)

    business, filing = common_setup(identifier, now)

    # The effective date cannot be a date prior to their Incorporation Date
    effective_date = now - datedelta.DAY
    business.founding_date = now
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()

    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert err

    business.founding_date = now - datedelta.YEAR
    with freeze_time(now):
        err = validate_effective_date(business, filing)
    assert not err


def test_validate_effective_date_not_before_other_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the new filing is not before an existing COD.

    Rules:
       - The effective date of change cannot be a date that
            is farther in the past as a previous COD filing(Standalone or AR).
    """
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_cod = copy.deepcopy(FILING_HEADER)
    filing_cod['filing']['header']['name'] = 'changeOfDirectors'
    filing_cod['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)

    business = Business(identifier=identifier,
                        founding_date=now - datedelta.datedelta(years=4)
                        )
    business.save()

    # create a COD
    factory_completed_filing(business=business,
                             data_dict=filing_cod,
                             filing_date=now)

    # move the COD BACK a MONTH
    filing_cod['filing']['header']['effectiveDate'] = (now - datedelta.MONTH).isoformat()

    # The effective date of change cannot be before the previous COD
    with freeze_time(now):
        err = validate_effective_date(business, filing_cod)
    assert err


def test_validate_effective_date_not_before_other_AR_with_COD(session):  # noqa: N802; COD is an acronym
    """Assert that the filing ordering rules are correct.

    Rules:
     - The effective date of change cannot be a date that is farther
            in the past as a previous COD filing(Standalone or AR).
    """
    # setup
    identifier = 'CP1234567'
    now = datetime(2001, 8, 5, 0, 0, 0, 0, tzinfo=timezone.utc)
    filing_ar = copy.deepcopy(ANNUAL_REPORT)
    filing_ar['filing']['changeOfDirectors'] = copy.deepcopy(CHANGE_OF_DIRECTORS)

    business = Business(identifier=identifier,
                        founding_date=now - datedelta.datedelta(years=4)
                        )
    business.save()

    # create a COD
    factory_completed_filing(business=business,
                             data_dict=filing_ar,
                             filing_date=now)

    # move the COD BACK a MONTH
    filing_ar['filing']['header']['effectiveDate'] = (now - datedelta.MONTH).isoformat()

    # The effective date of change cannot be before the previous COD
    with freeze_time(now):
        err = validate_effective_date(business, filing_ar)
    assert err
