# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure the Annual Report is validated correctly."""
import copy
from datetime import date, datetime

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Business
from legal_api.services.filings.validations.annual_report import validate


# from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing
@pytest.mark.parametrize(
    'test_name, now, ar_date, agm_date, expected_code, expected_msg',
    [('SUCCESS', date(2020, 9, 17), date(2020, 8, 5), date(2020, 7, 1), None, None),
     ])
def test_validate(session, test_name, now, ar_date, agm_date,
                  expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a basic AR can be validated."""
    # setup
    identifier = 'CP1234567'
    founding_date = ar_date - datedelta.YEAR
    business = Business(identifier=identifier, last_ledger_timestamp=founding_date)
    business.founding_date = datetime(founding_date.year, founding_date.month, founding_date.day)

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()

    # perform test
    with freeze_time(now):
        err = validate(business, ar)

    # validate outcomes
    assert not err
