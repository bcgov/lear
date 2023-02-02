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
from registry_schemas.example_data import FILING_HEADER, RESTORATION

from legal_api.models import Business, PartyRole
from legal_api.services.filings.validations.validation import validate
from legal_api.utils.legislation_datetime import LegislationDatetime

date_format = '%Y-%m-%d'
now = datetime.now().strftime(date_format)

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
relationships = ['Heir or Legal Representative', 'Director']


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
        ('invalid_party', 'Completing Party', 'Role can only be Applicant.'),
        ('no_party', None, 'Must have an Applicant.'),
        ('valid_party', 'Applicant', None),
    ]
)
def test_validate_party(session, test_name, party_role, expected_msg):
    """Assert that party is validated."""
    business = Business(identifier='BC1234567', legal_type='BC')
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['restoration'] = copy.deepcopy(RESTORATION)
    filing['filing']['header']['name'] = 'restoration'
    filing['filing']['restoration']['relationships'] = relationships

    if party_role:
        filing['filing']['restoration']['parties'][0]['roles'][0]['roleType'] = party_role
    else:
        filing['filing']['restoration']['parties'] = []
    err = validate(business, filing)

    if expected_msg:
        assert err
        assert err.msg[0]['error'] == expected_msg
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_status, restoration_type, expected_code, expected_msg',
    [
        ('SUCCESS', 'limitedRestoration', None, None),
        ('SUCCESS', 'limitedRestorationExtension', None, None),
        ('SUCCESS', 'fullRestoration', None, None),
        ('SUCCESS', 'limitedRestorationToFull', None, None),
        ('FAIL', 'fullRestoration', HTTPStatus.BAD_REQUEST, 'Applicants relationship is required.'),
        ('FAIL', 'limitedRestorationToFull', HTTPStatus.BAD_REQUEST, 'Applicants relationship is required.')
    ]
)
def test_validate_relationship(session, test_status, restoration_type, expected_code, expected_msg):
    """Assert that applicant's relationship is validated."""
    business = Business(identifier='BC1234567', legal_type='BC')

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['restoration'] = copy.deepcopy(RESTORATION)
    filing['filing']['header']['name'] = 'restoration'
    filing['filing']['restoration']['type'] = restoration_type

    if restoration_type in ('limitedRestoration', 'limitedRestorationExtension'):
        expiry_date = LegislationDatetime.now() + relativedelta(months=1)
        filing['filing']['restoration']['expiryDate'] = expiry_date.strftime(date_format)
    elif test_status == 'SUCCESS' and restoration_type in ('fullRestoration', 'limitedRestorationToFull'):
        filing['filing']['restoration']['relationships'] = relationships

    err = validate(business, filing)

    if expected_code:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, restoration_type, delta_date, is_valid',
    [
        ('greater', 'limitedRestoration', relativedelta(years=2), True),
        ('invalid_greater', 'limitedRestoration', relativedelta(years=2, days=1), False),
        ('lesser', 'limitedRestoration', relativedelta(months=1), True),
        ('invalid_lesser', 'limitedRestoration', relativedelta(days=25), False),

        ('greater', 'limitedRestorationExtension', relativedelta(years=2), True),
        ('invalid_greater', 'limitedRestorationExtension', relativedelta(years=2, days=1), False),
        ('lesser', 'limitedRestorationExtension', relativedelta(months=1), True),
        ('invalid_lesser', 'limitedRestorationExtension', relativedelta(days=25), False)
    ]
)
def test_validate_expiry_date(session, test_name, restoration_type, delta_date, is_valid):
    """Assert that expiry date is validated."""
    business = Business(identifier='BC1234567', legal_type='BC')
    expiry_date = LegislationDatetime.now()
    if delta_date:
        expiry_date = expiry_date + delta_date

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['restoration'] = copy.deepcopy(RESTORATION)
    filing['filing']['header']['name'] = 'restoration'

    filing['filing']['restoration']['type'] = restoration_type
    filing['filing']['restoration']['expiryDate'] = expiry_date.strftime(date_format)
    err = validate(business, filing)

    if is_valid:
        assert not err
    else:
        assert err


@pytest.mark.parametrize(
    'test_status, file_number, expected_code, expected_msg',
    [
        ('FAIL', None, HTTPStatus.BAD_REQUEST, 'Must provide Court Order Number.'),
        ('SUCCESS', '12345678901234567890', None, None)
    ]
)
def test_restoration_court_orders(session, test_status, file_number, expected_code, expected_msg):
    """Assert valid court orders."""
    business = Business(identifier='BC1234567', legal_type='BC')
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['restoration'] = copy.deepcopy(RESTORATION)
    filing['filing']['header']['name'] = 'restoration'
    filing['filing']['restoration']['relationships'] = relationships

    if file_number:
        court_order = {}
        court_order['fileNumber'] = file_number
        filing['filing']['restoration']['courtOrder'] = court_order
    else:
        del filing['filing']['restoration']['courtOrder']

    err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
