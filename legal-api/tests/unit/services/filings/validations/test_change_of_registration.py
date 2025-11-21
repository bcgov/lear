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

from legal_api.errors import Error
from legal_api.services.permissions import PermissionService
import pytest
from registry_schemas.example_data import CHANGE_OF_REGISTRATION_TEMPLATE, REGISTRATION

from legal_api.models import Business
from legal_api.services import NaicsService, NameXService, flags
from legal_api.services.filings.validations.change_of_registration import validate

from tests.unit.services.filings.validations import create_party, create_party_address


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
    'legalType': 'GP',
    'names': [{
        'name': REGISTRATION['nameRequest']['legalName'],
        'state': 'APPROVED',
        'consumptionDate': ''
    }]
}

naics_response = {
    'code': REGISTRATION['business']['naics']['naicsCode'],
    'classTitle': REGISTRATION['business']['naics']['naicsDescription']
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
    filing = copy.deepcopy(GP_CHANGE_OF_REGISTRATION)
    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)
    assert not err


def test_sp_change_of_registration(session):
    """Assert that the sole proprietor change of registration is valid."""
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = 'SP'

    filing = copy.deepcopy(SP_CHANGE_OF_REGISTRATION)
    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

    assert not err


def test_dba_change_of_registration(session):
    """Assert that the dba change of registration is valid."""
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = 'SP'

    filing = copy.deepcopy(DBA_CHANGE_OF_REGISTRATION)
    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

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

    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(invalid_nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

    assert err


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('sp_invalid_party', copy.deepcopy(SP_CHANGE_OF_REGISTRATION),
         '1 Proprietor and a Completing Party are required.'),
        ('dba_invalid_party', copy.deepcopy(DBA_CHANGE_OF_REGISTRATION),
         '1 Proprietor and a Completing Party are required.'),
        ('gp_invalid_party', copy.deepcopy(GP_CHANGE_OF_REGISTRATION),
         '2 Partners and a Completing Party are required.'),
    ]
)
def test_change_of_registration_parties_missing_role(session, test_name, filing, expected_msg):
    """Assert that change of registration party roles can be validated for missing roles."""
    filing['filing']['changeOfRegistration']['parties'][0]['roles'] = []

    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = filing['filing']['changeOfRegistration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

    assert err
    assert err.msg[0]['error'] == expected_msg

@pytest.mark.parametrize(
    'filing, legal_type, parties, expected_msg',
    [
        (
            copy.deepcopy(SP_CHANGE_OF_REGISTRATION),
            Business.LegalTypes.SOLE_PROP.value,
            [{'partyName': 'proprietor1', 'roles': ['Custodian']}],
            'Invalid party role(s) provided: custodian.'
        ),
        (
            copy.deepcopy(GP_CHANGE_OF_REGISTRATION),
            Business.LegalTypes.PARTNERSHIP.value,
            [
                {'partyName': 'partner1', 'roles': ['Partner']},
                {'partyName': 'partner2', 'roles': ['Liquidator']}
            ],
            'Invalid party role(s) provided: liquidator.'
        ),
    ]
)
def test_change_of_registration_parties_invalid_role(mocker, app, session, jwt, filing, legal_type, parties, expected_msg):
    """Assert that change of registration party roles can be validated for invalid roles."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    base_mailing_address = filing['filing']['changeOfRegistration']['parties'][0]['mailingAddress']
    base_delivery_address = filing['filing']['changeOfRegistration']['parties'][0]['deliveryAddress']

    filing['filing']['changeOfRegistration']['parties'] = []

    for index, party in enumerate(parties):
        mailing_addr = create_party_address(base_address=base_mailing_address)
        delivery_addr = create_party_address(base_address=base_delivery_address)
        p = create_party(party['roles'], index + 1, mailing_addr, delivery_addr)
        filing['filing']['changeOfRegistration']['parties'].append(p)

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = filing['filing']['changeOfRegistration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

    assert err is not None
    assert err.msg[0]['error'] == expected_msg
    assert '/filing/changeOfRegistration/parties/roles' in err.msg[0]['path']    


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
    filing['filing']['changeOfRegistration']['offices']['businessOffice']['deliveryAddress']['addressRegion'] = \
        'invalid'
    filing['filing']['changeOfRegistration']['offices']['businessOffice']['deliveryAddress']['addressCountry'] = \
        'invalid'

    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = filing['filing']['changeOfRegistration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

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

    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(business, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err

@patch.object(flags, 'is_on', return_value=True)
@patch('legal_api.services.filings.validations.change_of_registration.find_updated_keys_for_firms')
def test_change_of_registration_permission_checks(mock_flags,
    mock_find_keys, session
):
    """Assert that permission checks are called during change of registration validation."""
    filing = copy.deepcopy(SP_CHANGE_OF_REGISTRATION)
    business = Business(identifier=filing['filing']['business']['identifier'],
                        legal_type=filing['filing']['business']['legalType'])

    mock_find_keys.return_value = [{
        'is_dba': False,
        'name_changed': False,
        'address_changed': False,
        'delivery_address_changed': False,
        'email_changed': True
    }]
    error = Error(HTTPStatus.FORBIDDEN, [{'error': 'Permission Denied - You do not have permissions edit DBA in this filing.'}])
    with patch.object(PermissionService, 'check_user_permission', return_value=error):
        err = validate(business, filing)
    assert err
    assert err.code == HTTPStatus.FORBIDDEN
    assert 'DBA' in err.msg[0]['message']

    mock_find_keys.return_value = [{
        'is_dba': False,
        'name_changed': False,
        'address_changed': False,
        'delivery_address_changed': False,
        'email_changed': True
    }]
    error = Error(HTTPStatus.FORBIDDEN, [{'error': 'Permission Denied - You do not have permissions edit email in this filing.'}])
    with patch.object(PermissionService, 'check_user_permission', return_value=error):
        err = validate(business, filing)
    assert err
    assert err.code == HTTPStatus.FORBIDDEN
    assert 'email' in err.msg[0]['message']