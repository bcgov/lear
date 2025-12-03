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
from legal_api.services import NameXService
from legal_api.services.filings.validations.conversion import validate
from tests.unit.models import factory_business

from tests.unit.services.filings.validations import create_party, create_party_address


now = datetime.now().strftime('%Y-%m-%d')


GP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
GP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
GP_CONVERSION['filing']['business']['legalType'] = 'GP'
GP_CONVERSION['filing']['conversion']['nameRequest']['legalType'] = 'GP'
GP_CONVERSION['filing']['conversion']['startDate'] = '2019-01-01'

SP_CONVERSION = copy.deepcopy(CONVERSION_FILING_TEMPLATE)
SP_CONVERSION['filing']['conversion'] = copy.deepcopy(FIRMS_CONVERSION)
SP_CONVERSION['filing']['conversion']['startDate'] = '2019-01-01'
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
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type='GP',
                                state=Business.State.ACTIVE)
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = business.legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        err = validate(business, GP_CONVERSION)
    assert not err


def test_sp_conversion(session):
    """Assert that the sole proprietor conversion is valid."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type='SP',
                                state=Business.State.ACTIVE)
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = business.legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        err = validate(business, SP_CONVERSION)

    assert not err


def test_invalid_nr_conversion(session):
    """Assert that nr is invalid."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type='SP',
                                state=Business.State.ACTIVE)
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
        err = validate(business, filing)

    assert err


@pytest.mark.parametrize(
    'test_name, legal_type, filing, expected_msg',
    [
        ('sp_invalid_party', 'SP', copy.deepcopy(SP_CONVERSION),
         '1 Proprietor and a Completing Party are required.'),
        ('gp_invalid_party', 'GP', copy.deepcopy(GP_CONVERSION),
         '2 Partners and a Completing Party are required.'),
    ]
)
def test_conversion_parties_missing_role(session, test_name, legal_type, filing, expected_msg):
    """Assert that conversion party roles can be validated for missing roles."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type=legal_type,
                                state=Business.State.ACTIVE)
    filing['filing']['conversion']['parties'][0]['roles'] = []
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        err = validate(business, filing)

    assert err
    assert err.msg[0]['error'] == expected_msg

@pytest.mark.parametrize(
    'filing, legal_type, parties, expected_msg',
    [
        (
            copy.deepcopy(SP_CONVERSION),
            Business.LegalTypes.SOLE_PROP.value,
            [{'partyName': 'proprietor1', 'roles': ['Custodian']}],
            'Invalid party role(s) provided: custodian.'
        ),
        (
            copy.deepcopy(GP_CONVERSION),
            Business.LegalTypes.PARTNERSHIP.value,
            [
                {'partyName': 'partner1', 'roles': ['Partner']},
                {'partyName': 'partner2', 'roles': ['Liquidator']}
            ],
            'Invalid party role(s) provided: liquidator.'
        ),
    ]
)
def test_conversion_parties_invalid_role(session, filing, legal_type, parties, expected_msg):
    """Assert that conversion party roles can be validated for invalid roles."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type=legal_type,
                                state=Business.State.ACTIVE)

    base_mailing_address = filing['filing']['conversion']['parties'][0]['mailingAddress']
    base_delivery_address = filing['filing']['conversion']['parties'][0]['deliveryAddress']

    filing['filing']['conversion']['parties'] = []

    for index, party in enumerate(parties):
        mailing_addr = create_party_address(base_address=base_mailing_address)
        delivery_addr = create_party_address(base_address=base_delivery_address)
        p = create_party(party['roles'], index + 1, mailing_addr, delivery_addr)
        filing['filing']['conversion']['parties'].append(p)

    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        err = validate(business, filing)

    assert err is not None
    assert err.msg[0]['error'] == expected_msg
    assert '/filing/conversion/parties/roles' in err.msg[0]['path']


@pytest.mark.parametrize(
    'test_name, legal_type, filing',
    [
        ('sp_invalid_business_address', 'SP', copy.deepcopy(SP_CONVERSION)),
        ('gp_invalid_business_address', 'GP', copy.deepcopy(GP_CONVERSION)),
    ]
)
def test_invalid_business_address(session, test_name, legal_type, filing):
    """Assert that delivery business address is invalid."""
    registration_date = datetime(year=2020, month=6, day=10, hour=5, minute=55, second=13)
    business = factory_business('FM1234567', founding_date=registration_date, last_ar_date=None,
                                entity_type=legal_type,
                                state=Business.State.ACTIVE)
    filing['filing']['conversion']['offices']['businessOffice']['deliveryAddress']['addressRegion'] = \
        'invalid'
    filing['filing']['conversion']['offices']['businessOffice']['deliveryAddress']['addressCountry'] = \
        'invalid'
    nr_res = copy.deepcopy(nr_response)
    nr_res['legalType'] = legal_type
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_res)):
        err = validate(business, filing)

    assert err
    assert err.msg[0]['error'] == "Address Region must be 'BC'."
    assert err.msg[1]['error'] == "Address Country must be 'CA'."
