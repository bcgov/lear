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
"""Test suite to ensure Conversion is validated correctly."""
import copy
from datetime import datetime
from unittest.mock import patch

import pytest
from registry_schemas.example_data import CONVERSION_FILING_TEMPLATE, FIRMS_CONVERSION

from legal_api.models import Business
from legal_api.services import  NameXService
from legal_api.services.filings.validations.conversion import validate
from tests.unit.models import factory_business


now = datetime.now().strftime('%Y-%m-%d')


GP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
GP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
GP_CONVERSION['filing']['business']['legalType'] = 'GP'
GP_CONVERSION['filing']['conversion']['nameRequest']['legalType'] = 'GP'

SP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
SP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
SP_CONVERSION['filing']['business']['legalType'] = 'SP'
SP_CONVERSION['filing']['conversion']['nameRequest']['legalType'] = 'SP'
del SP_CONVERSION['filing']['conversion']['parties'][1]
SP_CONVERSION['filing']['conversion']['parties'][0]['roles'] = [
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
        'name': FIRMS_CONVERSION['nameRequest']['legalName'],
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


def test_gp_conversion(session):
    """Assert that the general partnership conversion is valid."""
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
            err = validate(GP_CONVERSION)
    assert not err


def test_sp_conversion(session):
    """Assert that the sole proprietor conversion is valid."""
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
            err = validate(SP_CONVERSION)

    assert not err


def test_invalid_nr_conversion(session):
    """Assert that nr is invalid."""
    filing = copy.deepcopy(SP_CONVERSION)
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
        ('sp_invalid_party', copy.deepcopy(SP_CONVERSION),
         '1 Proprietor and a Completing Party is required.'),
        ('gp_invalid_party', copy.deepcopy(GP_CONVERSION),
         '2 Partners and a Completing Party is required.'),
    ]
)
def test_invalid_party(session, test_name, filing, expected_msg):
    """Assert that party is invalid."""
    filing['filing']['conversion']['parties'][0]['roles'] = []
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
            err = validate(filing)

    assert err
    assert err.msg[0]['error'] == expected_msg


@pytest.mark.parametrize(
    'test_name, filing',
    [
        ('sp_invalid_business_address', copy.deepcopy(SP_CONVERSION)),
        ('gp_invalid_business_address', copy.deepcopy(GP_CONVERSION)),
    ]
)
def test_invalid_business_address(session, test_name, filing):
    """Assert that delivery business address is invalid."""
    filing['filing']['conversion']['offices']['businessOffice']['deliveryAddress']['addressRegion'] = \
        'invalid'
    filing['filing']['conversion']['offices']['businessOffice']['deliveryAddress']['addressCountry'] = \
        'invalid'
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
            err = validate(filing)

    assert err
    assert err.msg[0]['error'] == "Address Region must be 'BC'."
    assert err.msg[1]['error'] == "Address Country must be 'CA'."


@pytest.mark.parametrize(
    'test_name, legal_type, start_date, filing, expected_msg',
    [
        ('sp_invalid_start_date', 'SP', '2016-01-01', copy.deepcopy(SP_CONVERSION),
         'Start Date must be less than or equal to 2 years in the past and \
          less than or equal to 90 days in the future from the registration date.'),
        ('gp_invalid_start_date', 'GP', '2016-01-01', copy.deepcopy(GP_CONVERSION),
         'Start Date must be less than or equal to 2 years in the past and \
          less than or equal to 90 days in the future from the registration date.'),
        ('sp_valid_start_date', 'SP', '2019-01-01', copy.deepcopy(SP_CONVERSION), None),
        ('gp_valid_start_date', 'GP', '2019-01-01', copy.deepcopy(GP_CONVERSION), None),
    ]
)
def test_invalid_start_date(session, test_name, legal_type, start_date,  filing, expected_msg):
    """Assert that party is invalid."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type=legal_type,
                                state=Business.State.ACTIVE)
    filing['filing']['conversion']['startDate'] = start_date
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response)):
        err = validate(business, filing)

    if test_name in ['sp_valid_start_date', 'gp_valid_start_date']:
        assert not err
    else:
        assert err
        assert err.msg[0]['error'] == expected_msg
