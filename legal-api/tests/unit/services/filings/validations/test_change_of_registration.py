# Copyright © 2022 Province of British Columbia
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
"""Test suite to ensure Change of Registration is validated correctly."""
import copy
from datetime import datetime
from unittest.mock import patch
from http import HTTPStatus

import pytest
from registry_schemas.example_data import CHANGE_OF_REGISTRATION_TEMPLATE, REGISTRATION

from legal_api.services.filings.validations.change_of_registration import validate
from legal_api.services.namex import NameXService


now = datetime.now().strftime('%Y-%m-%d')

GP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
GP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'].append(REGISTRATION['parties'][1])

SP_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
SP_CHANGE_OF_REGISTRATION['filing']['business']['legalType'] = 'SP'
SP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['nameRequest']['legalType'] = 'SP'
SP_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]


DBA_CHANGE_OF_REGISTRATION = copy.deepcopy(CHANGE_OF_REGISTRATION_TEMPLATE)
DBA_CHANGE_OF_REGISTRATION['filing']['business']['legalType'] = 'SP'
DBA_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['nameRequest']['legalType'] = 'SP'
DBA_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['businessType'] = 'DBA'
DBA_CHANGE_OF_REGISTRATION['filing']['changeOfRegistration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'
    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'
    }
]

nr_response = {
    'state': 'APPROVED',
    'expirationDate': '',
    'names': [{
        'name': 'legal_name',
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


def test_gp_change_of_registration(session):
    """Assert that the general partnership change of registration is valid."""
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(GP_CHANGE_OF_REGISTRATION)
    assert not err


def test_sp_change_of_registration(session):
    """Assert that the sole proprietor change of registration is valid."""
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(SP_CHANGE_OF_REGISTRATION)

    assert not err


def test_dba_change_of_registration(session):
    """Assert that the dba change of registration is valid."""
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(DBA_CHANGE_OF_REGISTRATION)

    assert not err


def test_invalid_nr_change_of_registration(session):
    """Assert that nr is invalid."""
    filing = copy.deepcopy(SP_CHANGE_OF_REGISTRATION)
    invalid_nr_response = {
        'state': 'INPROGRESS',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name',
            'state': 'INPROGRESS',
            'consumptionDate': ''
        }]
    }
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(invalid_nr_response)):
        err = validate(filing)

    assert err


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('sp_invalid_party', copy.deepcopy(SP_CHANGE_OF_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('dba_invalid_party', copy.deepcopy(DBA_CHANGE_OF_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('gp_invalid_party', copy.deepcopy(GP_CHANGE_OF_REGISTRATION), '2 Partners and a Completing Party is required.'),
    ]
)
def test_invalid_party(session, test_name, filing, expected_msg):
    """Assert that party is invalid."""
    filing['filing']['changeOfRegistration']['parties'][0]['roles'] = []
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(filing)

    assert err
    assert err.msg[0]['error'] == expected_msg


@pytest.mark.parametrize(
    'test_name, filing',
    [
        ('sp_invalid_business_address', copy.deepcopy(SP_CHANGE_OF_REGISTRATION)),
        ('dba_invalid_business_address', copy.deepcopy(DBA_CHANGE_OF_REGISTRATION)),
        ('gp_invalid_business_address', copy.deepcopy(GP_CHANGE_OF_REGISTRATION)),
    ]
)
def test_invalid_business_address(session, test_name, filing):
    """Assert that delivery business address is invalid."""
    filing['filing']['changeOfRegistration']['businessAddress']['deliveryAddress']['addressRegion'] = 'invalid'
    filing['filing']['changeOfRegistration']['businessAddress']['deliveryAddress']['addressCountry'] = 'invalid'
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(filing)

    assert err
    assert err.msg[0]['error'] == "Address Region must be 'BC'."
    assert err.msg[1]['error'] == "Address Country must be 'CA'."


@pytest.mark.parametrize(
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', None, 'planOfArrangement', HTTPStatus.BAD_REQUEST, 'Court order file number is required.'),
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_change_of_registration_court_orders(session, test_status, file_number, effect_of_order,
                                             expected_code, expected_msg):
    """Assert valid court order."""
    filing = copy.deepcopy(GP_CHANGE_OF_REGISTRATION)

    court_order = {'effectOfOrder': effect_of_order}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['changeOfRegistration']['courtOrder'] = court_order

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
