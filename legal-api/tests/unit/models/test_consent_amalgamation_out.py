# Copyright © 2025 Province of British Columbia
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

"""Tests to assure the ConsentAmalgamationOut Model.

Test-Suite to ensure that the ConsentAmalgamationOut Model is working as expected.
"""
import datedelta
import copy
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from registry_schemas.example_data import (
    CONSENT_AMALGAMATION_OUT,
    FILING_HEADER,
)

from legal_api.models.consent_amalgamation_out import ConsentAmalgamationOut
from legal_api.utils.legislation_datetime import LegislationDatetime

from tests.unit.models import (
    factory_business,
    factory_completed_filing,
)


def test_consent_amalgamation_out_save(session):
    """Assert that the consent_amalgamation_out was saved."""
    business = factory_business('BC1234567')
    filing_dict = copy.deepcopy(FILING_HEADER)
    filing_dict['filing']['consentAmalgamationOut'] = copy.deepcopy(CONSENT_AMALGAMATION_OUT)
    filing = factory_completed_filing(business, filing_dict)

    expiry_date = get_cco_expiry_date(filing.effective_date)

    consent_amalgamation_out = ConsentAmalgamationOut()
    consent_amalgamation_out.consent_type = ConsentAmalgamationOut.ConsentTypes.amalgamation_out
    consent_amalgamation_out.foreign_jurisdiction = 'CA'
    consent_amalgamation_out.foreign_jurisdiction_region = 'AB'
    consent_amalgamation_out.expiry_date = expiry_date
    consent_amalgamation_out.business_id = business.id
    consent_amalgamation_out.filing_id = filing.id
    consent_amalgamation_out.save()

    assert consent_amalgamation_out.id


def test_get_active_cco(session):
    """Assert that the active consent_amalgamation_out can be retrieved."""
    business = factory_business('BC1234567')
    filing_dict = copy.deepcopy(FILING_HEADER)
    filing_dict['filing']['consentAmalgamationOut'] = copy.deepcopy(CONSENT_AMALGAMATION_OUT)
    filing = factory_completed_filing(business, filing_dict)

    expiry_date = get_cco_expiry_date(filing.effective_date)

    consent_amalgamation_out = ConsentAmalgamationOut()
    consent_amalgamation_out.consent_type = ConsentAmalgamationOut.ConsentTypes.amalgamation_out
    consent_amalgamation_out.foreign_jurisdiction = 'CA'
    consent_amalgamation_out.foreign_jurisdiction_region = 'AB'
    consent_amalgamation_out.expiry_date = expiry_date
    consent_amalgamation_out.business_id = business.id
    consent_amalgamation_out.filing_id = filing.id
    consent_amalgamation_out.save()

    cco = consent_amalgamation_out.get_active_cco(business.id, filing.effective_date)
    assert cco
    cco = consent_amalgamation_out.get_active_cco(business.id, expiry_date)
    assert cco
    cco = consent_amalgamation_out.get_active_cco(business.id, expiry_date, 'CA', 'AB')
    assert cco

    cco = consent_amalgamation_out.get_active_cco(business.id, expiry_date + datedelta.datedelta(days=1))
    assert not cco


def get_cco_expiry_date(filing_effective_date):
    effective_date = LegislationDatetime.as_legislation_timezone(filing_effective_date)
    _date = effective_date.replace(hour=23, minute=59, second=0, microsecond=0)
    _date += datedelta.datedelta(months=6)

    # Setting legislation timezone again after adding 6 months to recalculate the UTC offset and DST info
    _date = LegislationDatetime.as_legislation_timezone(_date)

    # Adjust day light savings. Handle DST +-1 hour changes
    dst_offset_diff = effective_date.dst() - _date.dst()
    _date += dst_offset_diff

    return LegislationDatetime.as_utc_timezone(_date)
