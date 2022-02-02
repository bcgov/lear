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
from dateutil.relativedelta import relativedelta
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, REGISTRATION

from legal_api.services.filings.validations.registration import validate
from legal_api.utils.legislation_datetime import LegislationDatetime


GP_REGISTRATION = copy.deepcopy(FILING_HEADER)
GP_REGISTRATION['filing']['header']['name'] = 'registration'
GP_REGISTRATION['filing']['business']['legalType'] = 'GP'
GP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
GP_REGISTRATION['filing']['registration']['startDate'] = datetime.now().strftime('%Y-%m-%d')

SP_REGISTRATION = copy.deepcopy(FILING_HEADER)
SP_REGISTRATION['filing']['header']['name'] = 'registration'
SP_REGISTRATION['filing']['business']['legalType'] = 'SP'
SP_REGISTRATION['filing']['registration'] = copy.deepcopy(REGISTRATION)
SP_REGISTRATION['filing']['registration']['startDate'] = datetime.now().strftime('%Y-%m-%d')
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
DBA_REGISTRATION['filing']['registration']['startDate'] = datetime.now().strftime('%Y-%m-%d')
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
        'incorporationNumber': 'BC1234567',
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


def test_gp_registration(session):
    """Assert that the general partnership registration is valid."""
    err = validate(GP_REGISTRATION)
    assert not err


def test_sp_registration(session):
    """Assert that the general partnership registration is valid."""
    err = validate(SP_REGISTRATION)
    assert not err


def test_dba_registration(session):
    """Assert that the general partnership registration is valid."""
    err = validate(DBA_REGISTRATION)
    assert not err


def test_business_type_required(session):
    """Assert that business type is required."""
    filing = copy.deepcopy(SP_REGISTRATION)
    del filing['filing']['registration']['businessType']
    err = validate(filing)
    assert err


@pytest.mark.parametrize(
    'test_name, filing, expected_msg',
    [
        ('sp_invalid_party', copy.deepcopy(SP_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('dba_invalid_party', copy.deepcopy(DBA_REGISTRATION), '1 Proprietor and a Completing Party is required.'),
        ('gp_invalid_party', copy.deepcopy(GP_REGISTRATION), '2 Partners and a Completing Party is required.'),
    ]
)
def test_invalid_party(session, test_name, filing, expected_msg):
    """Assert that party is invalid."""
    filing['filing']['registration']['parties'] = []
    err = validate(filing)
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
def test_invalid_business_address(session, test_name, filing):
    """Assert that delivery business address is invalid."""
    filing['filing']['registration']['businessAddress']['deliveryAddress']['addressRegion'] = 'invalid'
    filing['filing']['registration']['businessAddress']['deliveryAddress']['addressCountry'] = 'invalid'
    err = validate(filing)
    assert err
    assert err.msg[0]['error'] == "Address Region must be 'BC'."
    assert err.msg[1]['error'] == "Address Country must be 'CA'."


@pytest.mark.parametrize(
    'test_name, delta_date, is_valid',
    [
        ('today', None, True),
        ('greater', timedelta(days=90), True),
        ('invalid_greater', timedelta(days=91), False),
        ('lesser', relativedelta(years=-2), True),
        ('invalid_lesser', relativedelta(years=-2, days=-1), False)
    ]
)
def test_validate_start_date(session, test_name, delta_date, is_valid):
    """Assert that start date is validated."""
    start_date = LegislationDatetime.now()
    if delta_date:
        start_date = start_date + delta_date

    filing = copy.deepcopy(SP_REGISTRATION)
    filing['filing']['registration']['startDate'] = start_date.strftime('%Y-%m-%d')
    err = validate(filing)

    if is_valid:
        assert not err
    else:
        assert err


@pytest.mark.parametrize(
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', None, 'planOfArrangement', HTTPStatus.BAD_REQUEST, 'Court order file number is required.'),
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_registration_court_orders(session, test_status, file_number, effect_of_order, expected_code, expected_msg):
    """Assert valid court orders."""
    filing = copy.deepcopy(GP_REGISTRATION)

    court_order = {'effectOfOrder': effect_of_order}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['registration']['courtOrder'] = court_order

    err = validate(filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err
