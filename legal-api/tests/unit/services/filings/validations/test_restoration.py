# Copyright © 2023 Province of British Columbia
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
"""Test suite to ensure Restoration is validated correctly."""
import copy
from datetime import datetime
from dateutil.relativedelta import relativedelta
from http import HTTPStatus

import pytest
from registry_schemas.example_data import RESTORATION

from legal_api.models import PartyRole
from legal_api.services.filings.validations.restoration import validate
from legal_api.utils.legislation_datetime import LegislationDatetime


now = datetime.now().strftime('%Y-%m-%d')

legal_name = 'Test name request'
nr_response = {
    'state': 'APPROVED',
    'expirationDate': '',
    'names': [{
        'name': legal_name,
        'state': 'APPROVED',
        'consumptionDate': ''
    }]
}


class MockResponse:
    """Mock http response."""

    def __init__(self, json_data):
        """Initialize mock http response."""
        self.json_data = json_data

    def json(self):
        """Return mock json data."""
        return self.json_data


@pytest.mark.parametrize(
    'test_name, party_role, expected_msg',
    [
        ('invalid_party', PartyRole.RoleTypes.COMPLETING_PARTY.value, 'Role can only be Applicant.'),
        ('no_party', None, 'Must have an Applicant.'),
        ('valid_party', PartyRole.RoleTypes.APPLICANT.value, None),
    ]
)
def test_invalid_party(session, test_name, party_role, expected_msg):
    """Assert that party is invalid."""
    filing = copy.deepcopy(RESTORATION)
    if party_role:
        filing['filing']['restoration']['parties'][0]['roles'][0]['roleType'] = party_role
    else:
        filing['filing']['restoration']['parties'] = []
    err = validate(filing)

    assert err
    assert err.msg[0]['error'] == expected_msg


@pytest.mark.parametrize(
    'test_name, restoration_type, delta_date, is_valid',
    [
        ('greater', 'limitedRestoration', relativedelta(years=2), True),
        ('invalid_greater', 'limitedRestoration', relativedelta(years=2, days=1), False),
        ('lesser', 'limitedRestoration', relativedelta(months=1), True),
        ('invalid_lesser', 'limitedRestoration', relativedelta(days=29), False),

        ('greater', 'limitedRestorationExtension', relativedelta(years=2), True),
        ('invalid_greater', 'limitedRestorationExtension', relativedelta(years=2, days=1), False),
        ('lesser', 'limitedRestorationExtension', relativedelta(months=1), True),
        ('invalid_lesser', 'limitedRestorationExtension', relativedelta(days=29), False)
    ]
)
def test_validate_expiry_date(session, test_name, restoration_type, delta_date, is_valid):
    """Assert that expiry date is validated."""
    expiry_date = LegislationDatetime.now()
    if delta_date:
        expiry_date = expiry_date + delta_date

    filing = copy.deepcopy(RESTORATION)
    filing['filing']['restoration']['type'] = restoration_type
    filing['filing']['restoration']['expiryDate'] = expiry_date.strftime('%Y-%m-%d')
    err = validate(filing)

    if is_valid:
        assert not err
    else:
        assert err


@pytest.mark.parametrize(
    'test_status, file_number, expected_code, expected_msg',
    [
        ('FAIL', None, HTTPStatus.BAD_REQUEST, 'Court order file number is required.'),
        ('SUCCESS', '12345678901234567890', None, None)
    ]
)
def test_restoration_court_orders(session, test_status, file_number, expected_code, expected_msg):
    """Assert valid court orders."""
    filing = copy.deepcopy(RESTORATION)

    court_order = {}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['restoration']['courtOrder'] = court_order

    err = validate(filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
