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

from legal_api.models import Business
from legal_api.services.filings.validations.validation import validate
from legal_api.utils.legislation_datetime import LegislationDatetime

date_format = '%Y-%m-%d'
now = datetime.now().strftime(date_format)

legal_name = 'Test name request'
validate_nr_result = {
    'is_consumable': True,
    'is_approved': True,
    'is_expired': False,
    'consent_required': False,
    'consent_received': False
}

nr_response = {
    'state': 'APPROVED',
    'expirationDate': '',
    'legalType': 'BC',
    'names': [{
        'name': legal_name,
        'state': 'APPROVED',
        'consumptionDate': ''
    }]
}
relationships = ['Heir or Legal Representative', 'Director']


class MockResponse:
    """Mock http response."""

    def __init__(self, json_data, status_code):
        """Initialize mock http response."""
        self.json_data = json_data
        self.status_code = status_code

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
    filing['filing']['restoration']['nameRequest']['legalName'] = legal_name

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
    filing['filing']['restoration']['nameRequest']['legalName'] = legal_name

    if restoration_type in ('limitedRestoration', 'limitedRestorationExtension'):
        expiry_date = LegislationDatetime.now() + relativedelta(months=1)
        filing['filing']['restoration']['expiry'] = expiry_date.strftime(date_format)
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
        ('missing', 'limitedRestoration', None, False),

        ('greater', 'limitedRestorationExtension', relativedelta(years=2), True),
        ('invalid_greater', 'limitedRestorationExtension', relativedelta(years=2, days=1), False),
        ('lesser', 'limitedRestorationExtension', relativedelta(months=1), True),
        ('invalid_lesser', 'limitedRestorationExtension', relativedelta(days=25), False),
        ('missing', 'limitedRestorationExtension', None, False),
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
    filing['filing']['restoration']['nameRequest']['legalName'] = legal_name

    filing['filing']['restoration']['type'] = restoration_type
    if delta_date:
        filing['filing']['restoration']['expiry'] = expiry_date.strftime(date_format)
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
    filing['filing']['restoration']['nameRequest']['legalName'] = legal_name
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


@pytest.mark.parametrize(
    'test_status, filing_sub_type, legal_types, nr_number, nr_type, new_legal_name, expected_code, expected_msg',
    [
        # full restoration
        ('SUCCESS_NEW_NR', 'fullRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', 'RCC','new name', None, None),
        ('SUCCESS_NAME_ONLY', 'fullRestoration', ['BC', 'BEN', 'ULC', 'CC'], None, 'RCR', 'new name', None, None),
        ('FAIL_NO_NR_AND_NAME', 'fullRestoration', ['BC', 'BEN', 'ULC', 'CC'], None, 'BERE', None, HTTPStatus.BAD_REQUEST,
         'Legal name is missing in nameRequest.'),
        ('FAIL_NR_AND_NO_NAME', 'fullRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', 'RUL', None,
         HTTPStatus.BAD_REQUEST, 'Legal name is missing in nameRequest.'),
        ('FAIL_NO_NR_TYPE', 'fullRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', '', 'new name',
         HTTPStatus.BAD_REQUEST, 'The name type associated with the name request number entered cannot be used.'),

        # limited restoration
        ('SUCCESS_NEW_NR', 'limitedRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', 'RCC', 'new name', None, None),
        ('SUCCESS_NAME_ONLY', 'limitedRestoration', ['BC', 'BEN', 'ULC', 'CC'], None, 'RCR', 'new name', None, None),
        ('FAIL_NO_NR_AND_NAME', 'limitedRestoration', ['BC', 'BEN', 'ULC', 'CC'], None, 'BERE', None, HTTPStatus.BAD_REQUEST,
         'Legal name is missing in nameRequest.'),
        ('FAIL_NR_AND_NO_NAME', 'limitedRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', 'RUL', None,
         HTTPStatus.BAD_REQUEST, 'Legal name is missing in nameRequest.'),
        ('FAIL_NO_NR_TYPE', 'limitedRestoration', ['BC', 'BEN', 'ULC', 'CC'], 'NR 1234567', '', 'new name',
         HTTPStatus.BAD_REQUEST, 'The name type associated with the name request number entered cannot be used.'),
    ]
)
def test_restoration_nr(session, mocker, test_status, filing_sub_type, legal_types, nr_number, nr_type, new_legal_name,
                        expected_code, expected_msg):
    """Assert nr block of filing is validated correctly."""

    expiry_date = LegislationDatetime.now() + relativedelta(months=1)
    expiry_date_str = expiry_date.strftime(date_format)
    mocker.patch('legal_api.services.NameXService.validate_nr', return_value=validate_nr_result)

    for legal_type in legal_types:
        business = Business(identifier='BC1234567', legal_type=legal_type)
        filing = copy.deepcopy(FILING_HEADER)
        filing['filing']['restoration'] = copy.deepcopy(RESTORATION)
        filing['filing']['restoration']['type'] = filing_sub_type
        filing['filing']['restoration']['expiry'] = expiry_date_str
        filing['filing']['restoration']['relationships'] = relationships
        filing['filing']['restoration']['nameRequest']['legalType'] = legal_type
        if nr_number:
            filing['filing']['restoration']['nameRequest']['nrNumber'] = nr_number
        if new_legal_name:
            filing['filing']['restoration']['nameRequest']['legalName'] = new_legal_name

        temp_nr_response = copy.deepcopy(nr_response)
        temp_nr_response['legalType'] = legal_type
        temp_nr_response['names'][0]['name'] = new_legal_name
        temp_nr_response['requestTypeCd'] = nr_type
        mock_nr_response = MockResponse(temp_nr_response, HTTPStatus.OK)

        mocker.patch('legal_api.services.NameXService.query_nr_number', return_value=mock_nr_response)
        err = validate(business, filing)

        # validate outcomes
        if expected_code:
            assert expected_code == err.code
            assert expected_msg == err.msg[0]['error']
        else:
            assert not err
