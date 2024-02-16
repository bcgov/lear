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
"""Test suite to ensure Registration is validated correctly."""
import copy
from datetime import datetime, timedelta
from unittest.mock import patch
from dateutil.relativedelta import relativedelta
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, REGISTRATION

from legal_api.services import NaicsService, NameXService
from legal_api.services.filings.validations.validation import validate
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils.legislation_datetime import LegislationDatetime

from ...utils import helper_create_jwt

now = datetime.now().strftime('%Y-%m-%d')

GP_REGISTRATION = copy.deepcopy(FILING_HEADER)
GP_REGISTRATION['filing']['header']['name'] = 'registration'
GP_REGISTRATION['filing']['business']['legalType'] = 'GP'
GP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
GP_REGISTRATION['filing']['registration']['startDate'] = now

SP_REGISTRATION = copy.deepcopy(FILING_HEADER)
SP_REGISTRATION['filing']['header']['name'] = 'registration'
SP_REGISTRATION['filing']['business']['legalType'] = 'SP'
SP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
SP_REGISTRATION['filing']['registration']['startDate'] = now
SP_REGISTRATION['filing']['registration']['nameRequest']['legalType'] = 'SP'
SP_REGISTRATION['filing']['registration']['businessType'] = 'SP'
SP_REGISTRATION['filing']['registration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'

    },
    {
        'roleType': 'Proprietor',
        'appointmentDate': '2022-01-01'

    }
]
del SP_REGISTRATION['filing']['registration']['parties'][1]


DBA_REGISTRATION = copy.deepcopy(FILING_HEADER)
DBA_REGISTRATION['filing']['header']['name'] = 'registration'
DBA_REGISTRATION['filing']['business']['legalType'] = 'SP'
DBA_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
DBA_REGISTRATION['filing']['registration']['startDate'] = now
DBA_REGISTRATION['filing']['registration']['nameRequest']['legalType'] = 'SP'
DBA_REGISTRATION['filing']['registration']['businessType'] = 'DBA'
DBA_REGISTRATION['filing']['registration']['parties'][0]['roles'] = [
    {
        'roleType': 'Completing Party',
        'appointmentDate': '2022-01-01'
    }
]
DBA_REGISTRATION['filing']['registration']['parties'][1] = {
    'officer': {
        'id': 2,
        'organizationName': 'Xyz Inc.',
        'identifier': 'BC1234567',
        'taxId': '123456789',
        'email': 'peter@email.com',
        'partyType': 'organization'
    },
    'mailingAddress': {
        'streetAddress': 'mailing_address - address line one',
        'streetAddressAdditional': '',
        'addressCity': 'mailing_address city',
        'addressCountry': 'CA',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC'
    },
    'roles': [
        {
            'roleType': 'Proprietor',
            'appointmentDate': '2022-01-01'
        }
    ]
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


def _mock_nr_response(legal_type):
    return MockResponse({
        'state': 'APPROVED',
        'legalType': legal_type,
        'expirationDate': '',
        'names': [{
            'name': REGISTRATION['nameRequest']['legalName'],
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    })


def test_gp_registration(mocker, app, session, jwt):
    """Assert that the general partnership registration is valid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response('GP')):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, GP_REGISTRATION)

    assert not err


def test_sp_registration(mocker, app, session, jwt):
    """Assert that the general partnership registration is valid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response('SP')):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, SP_REGISTRATION)

    assert not err


def test_dba_registration(mocker, app, session, jwt):
    """Assert that the general partnership registration is valid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response('SP')):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, DBA_REGISTRATION)

    assert not err


def test_invalid_nr_registration(mocker, app, session, jwt):
    """Assert that nr is invalid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    filing = copy.deepcopy(SP_REGISTRATION)
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
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == 'Name Request is not approved.'


def test_business_type_required(mocker, app, session, jwt):
    """Assert that business type is required."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    filing = copy.deepcopy(SP_REGISTRATION)
    del filing['filing']['registration']['businessType']

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == 'Business Type is required.'


@pytest.mark.parametrize(
    'test_name, tax_id, expected',
    [
        ('invalid_taxId', '123456789BC0001', 'Can only provide BN9 for SP/GP registration.'),
        ('valid_taxId', '123456789', None)
    ]
)
def test_validate_tax_id(mocker, app, session, jwt, test_name, tax_id, expected):
    """Assert that taxId is validated."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    filing = copy.deepcopy(SP_REGISTRATION)
    filing['filing']['registration']['business']['taxId'] = tax_id

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    if expected:
        assert err
        assert err.msg[0]['error'] == expected
    else:
        assert err is None


def test_naics_invalid(mocker, app, session, jwt):
    """Assert that naics is invalid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    filing = copy.deepcopy(SP_REGISTRATION)
    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value={}):
            err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == 'Invalid naics code or description.'


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('sp_invalid_party', copy.deepcopy(SP_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('dba_invalid_party', copy.deepcopy(DBA_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('gp_invalid_party', copy.deepcopy(GP_REGISTRATION), '2 Partners and a Completing Party is required.'),
    ]
)
def test_invalid_party(mocker, app, session, jwt, test_name, filing, expected_msg):
    """Assert that party is invalid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client
    filing['filing']['registration']['parties'] = []

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == expected_msg


@pytest.mark.parametrize(
    'test_name, filing',
    [
        ('sp_invalid_business_address', copy.deepcopy(SP_REGISTRATION)),
        ('dba_invalid_business_address', copy.deepcopy(DBA_REGISTRATION)),
        ('gp_invalid_business_address', copy.deepcopy(GP_REGISTRATION)),
    ]
)
def test_invalid_business_address(mocker, app, session, jwt, test_name, filing):
    """Assert that delivery business address is invalid."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    filing['filing']['registration']['offices']['businessOffice']['deliveryAddress']['addressRegion'] = 'invalid'
    filing['filing']['registration']['offices']['businessOffice']['deliveryAddress']['addressCountry'] = 'invalid'

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == "Address Region must be 'BC'."
    assert err.msg[1]['error'] == "Address Country must be 'CA'."


@pytest.mark.parametrize(
    'test_name, username, roles, delta_date, is_valid',
    [
        ('staff_today', 'staff', STAFF_ROLE, None, True),
        ('staff_greater', 'staff', STAFF_ROLE, timedelta(days=90), True),
        ('staff_invalid_greater', 'staff', STAFF_ROLE, timedelta(days=91), False),
        ('staff_lesser', 'staff', STAFF_ROLE, relativedelta(years=-20), True),
        ('general_user_today', 'general', [BASIC_USER], None, True),
        ('general_user_greater', 'general', [BASIC_USER], timedelta(days=90), True),
        ('general_user_invalid_greater', 'general', [BASIC_USER], timedelta(days=91), False),
        ('general_user_lesser', 'general', [BASIC_USER], relativedelta(years=-10), True),
        ('general_user_invalid_lesser', 'general', [BASIC_USER], relativedelta(years=-10, days=-1), False)
    ]
)
def test_validate_start_date(mocker, app, session, jwt, test_name, username, roles, delta_date, is_valid):
    """Assert that start date is validated."""
    def mock_validate_roles(required_roles):
        if roles in required_roles:
            return True
        return False
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', side_effect=mock_validate_roles)  # Client

    start_date = LegislationDatetime.now()
    if delta_date:
        start_date = start_date + delta_date

    filing = copy.deepcopy(SP_REGISTRATION)
    filing['filing']['registration']['startDate'] = start_date.strftime('%Y-%m-%d')

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    if is_valid:
        assert not err
    else:
        assert err


@pytest.mark.parametrize(
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_registration_court_orders(mocker, app, session, jwt, test_status, file_number, effect_of_order, expected_code, expected_msg):
    """Assert valid court orders."""
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)

    filing = copy.deepcopy(GP_REGISTRATION)

    court_order = {'effectOfOrder': effect_of_order}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['registration']['courtOrder'] = court_order

    legal_type = filing['filing']['registration']['nameRequest']['legalType']
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        with patch.object(NaicsService, 'find_by_code', return_value=naics_response):
            err = validate(None, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
