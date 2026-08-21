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
"""Test suite to ensure Amalgamation Application is validated correctly."""
import copy
from unittest.mock import patch
from http import HTTPStatus
from datetime import date, datetime, timezone

import pytest
from freezegun import freeze_time

from business_model.models import (
    Address,
    AmalgamatingBusiness,
    Amalgamation,
    Business,
    Filing,
    Office,
    Party,
    PartyRole,
    Resolution,
    ShareClass,
    ShareSeries,
)
from legal_api.errors import Error
from legal_api.services import NameXService, STAFF_ROLE, BASIC_USER, flags
from legal_api.services.filings.validations.validation import validate
from legal_api.services.permissions import PermissionService
from registry_schemas.example_data import AMALGAMATION_APPLICATION

from tests.unit.models import factory_address, factory_business, factory_business_office
from tests.unit.services.filings.validations import create_party, create_party_address, lists_are_equal
from tests.unit.services.utils import jwt_request_context


class MockResponse:
    """Mock http response."""

    def __init__(self, json_data, status_code=HTTPStatus.OK):
        """Initialize mock http response."""
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        """Return mock json data."""
        return self.json_data


def _mock_nr_response(legal_type):
    return MockResponse({
        'state': 'APPROVED',
        'legalType': legal_type,
        'expirationDate': '',
        'names': [{
            'name': AMALGAMATION_APPLICATION['nameRequest']['legalName'],
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    })


def _get_amalg_template():
    """Return the Amalgamation Application filing template."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'authorizationReceived': True,
                                  'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['business'] = {'identifier': 'T1234567'}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    return filing


def test_invalid_nr_amalgamation(mocker, app, session):
    """Assert that nr is invalid."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    invalid_nr_response = {
        'state': 'INPROGRESS',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name',
            'state': 'INPROGRESS',
            'consumptionDate': ''
        }]
    }
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(invalid_nr_response)):
        err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == 'Name Request is not approved.'


@pytest.mark.parametrize(
    'amalgamation_type',
    [
        Amalgamation.AmalgamationTypes.horizontal.name,
        Amalgamation.AmalgamationTypes.vertical.name,
    ]
)
def test_short_form_amalgamation_rejects_nr(mocker, app, session, amalgamation_type):
    """Assert short-form amalgamations reject an nrNumber."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])
    with patch.object(NameXService, 'query_nr_number') as mock_query:
        err = validate(None, filing)

    assert err
    assert any(m['error'] == 'Short-form amalgamations cannot have a Name Request.' for m in err.msg)
    mock_query.assert_not_called()


@pytest.mark.parametrize(
    'amalgamation_type, expected_msg',
    [
        (Amalgamation.AmalgamationTypes.regular.name, 'At least one Director and a Completing Party is required.'),
        (Amalgamation.AmalgamationTypes.vertical.name, 'A Completing Party is required.'),
        (Amalgamation.AmalgamationTypes.horizontal.name, 'A Completing Party is required.'),
    ]
)
def test_amalgamation_parties_missing_role(mocker, app, session, amalgamation_type, expected_msg):
    """Assert that amalgamation party roles can be validated for missing roles."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    filing['filing']['amalgamationApplication']['parties'] = []
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == expected_msg

@pytest.mark.parametrize(
    'parties, expected_msg',
    [
        (
            [{'partyName': 'officer1', 'roles': ['Custodian']},],
            'Invalid party role(s) provided: custodian.'
        ),
        (
            [
                {'partyName': 'officer1', 'roles': ['Director']},
                {'partyName': 'officer2', 'roles': ['Liquidator']}
            ],
            'Invalid party role(s) provided: liquidator.'
        ),
    ]
)
def test_amalgamation_parties_invalid_role(mocker, app, session, parties, expected_msg):
    """Assert that amalgamation party roles can be validated for invalid roles."""
    filing = {'filing': {}}
    filing['filing']['header'] = {
        'name': 'amalgamationApplication',
        'date': '2019-04-08',
        'certifiedBy': 'full name',
        'authorizationReceived': True,
        'email': 'no_one@never.get',
        'filingId': 1
    }
    filing['filing']['business'] = {'identifier': 'T1234567'}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['type'] = Amalgamation.AmalgamationTypes.regular.name

    base_mailing_address = filing['filing']['amalgamationApplication']['parties'][0]['mailingAddress']
    base_delivery_address = filing['filing']['amalgamationApplication']['parties'][0]['deliveryAddress']

    filing['filing']['amalgamationApplication']['parties'] = []

    for index, party in enumerate(parties):
        mailing_addr = create_party_address(base_address=base_mailing_address)
        delivery_addr = create_party_address(base_address=base_delivery_address)
        p = create_party(party['roles'], index + 1, mailing_addr, delivery_addr)
        filing['filing']['amalgamationApplication']['parties'].append(p)

    mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_name_request',
        return_value=[]
    )
    mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
        return_value=[]
    )

    err = validate(None, filing)

    assert err is not None
    assert err.msg[0]['error'] == expected_msg
    assert '/filing/amalgamationApplication/parties/roles' in err.msg[0]['path']


@pytest.mark.parametrize(
    'test_name, legal_type, delivery_region, delivery_country, mailing_region, mailing_country, expected_code, expected_msg',
    [
        ('SUCCESS', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.BC_CCC.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.COMP.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BCOMP.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BC_ULC_COMPANY.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.COMP.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BC_CCC.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'AB', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.COMP.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_ALL_ADDRESS_REGIONS', Business.LegalTypes.BC_CCC.value, 'WA', 'CA', 'WA', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BCOMP.value, 'BC', 'NZ', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.COMP.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BC_CCC.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.COMP.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BC_CCC.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_ALL_ADDRESS', Business.LegalTypes.BCOMP.value, 'AB', 'NZ', 'AB', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/amalgamationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ])
    ])
def test_validate_amalgamation_office(session, mocker, test_name, legal_type, delivery_region,
                                      delivery_country, mailing_region, mailing_country, expected_code,
                                      expected_msg):
    """Assert that amalgamation offices can be validated."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)

    filing['filing']['amalgamationApplication']['nameRequest'] = {}
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    filing['filing']['amalgamationApplication']['contactPoint']['email'] = 'no_one@never.get'
    filing['filing']['amalgamationApplication']['contactPoint']['phone'] = '(123) 456-7890'

    regoffice = filing['filing']['amalgamationApplication']['offices']['registeredOffice']
    regoffice['deliveryAddress']['addressRegion'] = delivery_region
    regoffice['deliveryAddress']['addressCountry'] = delivery_country
    regoffice['mailingAddress']['addressRegion'] = mailing_region
    regoffice['mailingAddress']['addressCountry'] = mailing_country

    recoffice = filing['filing']['amalgamationApplication']['offices']['recordsOffice']
    recoffice['deliveryAddress']['addressRegion'] = delivery_region
    recoffice['deliveryAddress']['addressCountry'] = delivery_country
    recoffice['mailingAddress']['addressRegion'] = mailing_region
    recoffice['mailingAddress']['addressCountry'] = mailing_country

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    err = validate(None, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


def test_amalgamation_regular_requires_at_least_one_share_class(mocker, app, session):
    """Assert that a regular amalgamation with empty shareClasses returns a validation error."""
    filing = {'filing': {}}
    filing['filing']['header'] = {
        'name': 'amalgamationApplication',
        'date': '2019-04-08',
        'certifiedBy': 'full name',
        'authorizationReceived': True,
        'email': 'no_one@never.get',
        'filingId': 1
    }
    filing['filing']['business'] = {'identifier': 'T1234567'}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['type'] = Amalgamation.AmalgamationTypes.regular.name
    filing['filing']['amalgamationApplication']['shareStructure'] = {'shareClasses': []}

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    err = validate(None, filing)

    assert err is not None
    assert any(e['error'] == 'A company must have at least one Class of Shares.' and
               e['path'] == '/filing/amalgamationApplication/shareStructure/shareClasses'
               for e in err.msg)


@pytest.mark.parametrize(
    'test_name, legal_type,'
    'class_name_1,class_has_max_shares,class_max_shares,has_par_value,par_value,currency,'
    'series_name_1,series_has_max_shares,series_max_shares,'
    'class_name_2,series_name_2,'
    'expected_code, expected_msg',
    [
        ('SUCCESS', 'BEN', 'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BEN', 'Class 1 Shares', False, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BEN', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'BEN', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', None, None, None),
        ('FAIL-CLASS2', 'BEN',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 1 Shares', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares name already used in another share class.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BEN',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', 'Series 1 Shares',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares name already used in this share class.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BEN',
         'Class 1 Shares', True, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BEN',
         'Class 1 Shares', True, 5000, True, 0.875, None, 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BEN',
         'Class 1 Shares', True, 5000, True, None, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BEN',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BEN',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 10000,
         None, None,
            HTTPStatus.BAD_REQUEST, [{
                'error':
                'Series Series 1 Shares share quantity must be less than or equal to that of its class Class 1 Shares',
                'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
            }]),
        ('SUCCESS', 'BC', 'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BC', 'Class 1 Shares', False, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'BC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', None, None, None),
        ('FAIL-CLASS2', 'BC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 1 Shares', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares name already used in another share class.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', 'Series 1 Shares',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares name already used in this share class.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BC',
         'Class 1 Shares', True, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BC',
         'Class 1 Shares', True, 5000, True, 0.875, None, 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BC',
         'Class 1 Shares', True, 5000, True, None, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Series 1 Shares share quantity must be less than or equal to that of its class Class 1 Shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'ULC', 'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'ULC', 'Class 1 Shares', False, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'ULC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'ULC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', None, None, None),
        ('FAIL-CLASS2', 'ULC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 1 Shares', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares name already used in another share class.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'ULC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', 'Series 1 Shares',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares name already used in this share class.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'ULC',
         'Class 1 Shares', True, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'ULC',
         'Class 1 Shares', True, 5000, True, 0.875, None, 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'ULC',
         'Class 1 Shares', True, 5000, True, None, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'ULC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'ULC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Series 1 Shares share quantity must be less than or equal to that of its class Class 1 Shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'CC', 'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CC', 'Class 1 Shares', False, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'CC', 'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', None, None, None),
        ('FAIL-CLASS2', 'CC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 1 Shares', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares name already used in another share class.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CC',
         'Class 1 Shares', False, None, False, None, None, 'Series 1 Shares', False, None,
         'Class 2 Shares', 'Series 1 Shares',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares name already used in this share class.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CC',
         'Class 1 Shares', True, None, True, 0.875, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CC',
         'Class 1 Shares', True, 5000, True, 0.875, None, 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CC',
         'Class 1 Shares', True, 5000, True, None, 'CAD', 'Series 1 Shares', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Class 1 Shares must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Series 1 Shares must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CC',
         'Class 1 Shares', True, 5000, True, 0.875, 'CAD', 'Series 1 Shares', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Series 1 Shares share quantity must be less than or equal to that of its class Class 1 Shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }])
    ])
def test_validate_incorporation_share_classes(session, mocker, test_name, legal_type,
                                              class_name_1, class_has_max_shares, class_max_shares,
                                              has_par_value, par_value, currency, series_name_1, series_has_max_shares,
                                              series_max_shares,
                                              class_name_2, series_name_2,
                                              expected_code, expected_msg):
    """Assert that validator validates share class correctly."""
    filing = _get_amalg_template()

    filing['filing']['amalgamationApplication']['nameRequest'] = {}
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type

    share_structure = filing['filing']['amalgamationApplication']['shareStructure']

    share_structure['shareClasses'][0]['name'] = class_name_1
    share_structure['shareClasses'][0]['hasMaximumShares'] = class_has_max_shares
    share_structure['shareClasses'][0]['maxNumberOfShares'] = class_max_shares
    share_structure['shareClasses'][0]['hasParValue'] = has_par_value
    share_structure['shareClasses'][0]['parValue'] = par_value
    share_structure['shareClasses'][0]['currency'] = currency
    share_structure['shareClasses'][0]['series'][0]['name'] = series_name_1
    share_structure['shareClasses'][0]['series'][0]['hasMaximumShares'] = series_has_max_shares
    share_structure['shareClasses'][0]['series'][0]['maxNumberOfShares'] = series_max_shares

    if class_name_2:
        # set second shareClass name
        share_structure['shareClasses'][1]['name'] = class_name_2

    if series_name_2:
        # set 1st shareClass, 2nd series name
        share_structure['shareClasses'][0]['series'][1]['name'] = series_name_2

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    # perform test
    err = validate(None, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'amalgamation_type, expected_code',
    [
        (Amalgamation.AmalgamationTypes.regular.name, HTTPStatus.UNPROCESSABLE_ENTITY),
        (Amalgamation.AmalgamationTypes.vertical.name, None),
        (Amalgamation.AmalgamationTypes.horizontal.name, None),
    ]
)
def test_validate_amalgamation_office_or_share_required(session, mocker, amalgamation_type, expected_code):
    """Assert that amalgamation offices/shareStructure required can be validated."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type

    del filing['filing']['amalgamationApplication']['offices']
    del filing['filing']['amalgamationApplication']['shareStructure']

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    err = validate(None, filing)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_amalgamation_court_orders(mocker, app, session,
                                   test_status, file_number, effect_of_order, expected_code, expected_msg):
    """Assert valid court orders."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    court_order = {'effectOfOrder': effect_of_order}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['amalgamationApplication']['courtOrder'] = court_order

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])
    err = validate(None, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, 'Cannot amalgamate with BC1234567 which is in historical state.'),
        ('SUCCESS', None, None)
    ]
)
def test_is_business_historical(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses is historical."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value,
                        state=Business.State.ACTIVE if test_status == 'SUCCESS' else Business.State.HISTORICAL)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.resources.v2.business.business.AccountService.get_account_by_affiliated_identifier',
                 return_value={'orgs': [{'id': account_id}]} if test_status == 'SUCCESS' else {})

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, 'BC1234567 is frozen.'),
        ('SUCCESS', None, None)
    ]
)
def test_is_business_frozen(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert an admin-frozen amalgamating business cannot amalgamate, staff included."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value,
                        state=Business.State.ACTIVE,
                        admin_freeze=test_status == 'FAIL')

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(None, filing)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, 'BC1234567 has a draft, pending or future effective filing.'),
        ('SUCCESS', None, None)
    ]
)
def test_has_pending_filing(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses has draft, pending or future effective filing."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('business_model.models.business.Business.find_by_identifier',
                 return_value=Business(identifier='BC1234567',
                                       legal_type=Business.LegalTypes.BCOMP.value))
    mocker.patch('business_model.models.filing.Filing.get_filings_by_status',
                 return_value=[Filing()] if test_status == 'FAIL' else [])

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(None, filing)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, 'BC1234567 is part of a future effective amalgamation filing.'),
        ('SUCCESS', None, None)
    ]
)
def test_in_future_effective_amalgamation_filing(mocker, app, session, jwt,
                                                 test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses is part of a future effective amalgamation filing."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('business_model.models.business.Business.find_by_identifier',
                 return_value=Business(identifier='BC1234567',
                                       legal_type=Business.LegalTypes.BCOMP.value))
    mocker.patch('business_model.models.business.Business.is_pending_amalgamating_business',
                 return_value=[Filing()] if test_status == 'FAIL' else [])

    with jwt_request_context(app, jwt, [STAFF_ROLE]):
        err = validate(None, filing)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, flag_enabled, has_permission, expected_code, expected_msg',
    [
        ('FAIL_FLAG_OFF', False, False, HTTPStatus.BAD_REQUEST, ['BC1234567', 'BC7654321']),
         ('SUCCESS_AFFILIATED', False, False, None, None),
         ('FAIL_FLAG_ON_WITH_PERMISSION', True, False, HTTPStatus.BAD_REQUEST, 'BC1234567'),
        ('SUCCESS_FLAG_ON_WITH_PERMISSION', True, True, None, None)
    ]
)
def test_is_business_affliated(mocker, app, session, jwt, test_status, flag_enabled, has_permission, expected_code, expected_msg):
    """Assert valid amalgamating businesses is affliated."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234567'
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC7654321'
        }
    ]

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.resources.v2.business.business.AccountService.get_account_by_affiliated_identifier',
                 return_value={'orgs': [{'id': account_id}]} if test_status in  'SUCCESS_AFFILIATED' else {})

    mocker.patch.object(flags, 'is_on', return_value=flag_enabled)

    permission_error = None if has_permission else Error(
        HTTPStatus.BAD_REQUEST, [{'message': 'Permission Denied - You do not have permissions to amalgamate an unaffiliated business.'}])
    mocker.patch.object(PermissionService, 'check_user_permission', return_value=permission_error)

    mocker.patch('legal_api.services.filings.validations.common_validations.AccountService.get_contacts', return_value={'contacts': [{'email': 'test@example.com'}]})

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code is None:
        assert not err
    else:
        assert expected_code == err.code
        if isinstance(expected_msg, list):
            assert (f'{expected_msg[0]} is not affiliated with the currently selected BC Registries account.' ==
                    err.msg[0]['error'])
            assert (f'{expected_msg[1]} is not affiliated with the currently selected BC Registries account.' ==
                    err.msg[1]['error'])
        else:
            error_msg = err.msg[0].get('error') or err.msg[0].get('message')
            assert 'Permission Denied - You do not have permissions to amalgamate an unaffiliated business.' == error_msg


@pytest.mark.parametrize(
    'test_status, flag_enabled, has_permission, expected_code, expected_msg',
    [
        ('FAIL_FLAG_OFF', False, False, HTTPStatus.BAD_REQUEST, ['BC1234567', 'BC7654321']),
         ('SUCCESS_GOOD_STANDING', False, False, None, None),
         ('FAIL_FLAG_ON_WITH_PERMISSION', True, False, HTTPStatus.BAD_REQUEST, 'BC1234567'),
        ('SUCCESS_FLAG_ON_WITH_PERMISSION', True, True, None, None)
    ]

)
def test_is_business_in_good_standing(mocker, app, session, jwt, test_status, flag_enabled, has_permission, expected_code, expected_msg):
    """Assert valid amalgamating businesses is in good standing."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234567'
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC7654321'
        }
    ]

    def mock_find_by_identifier(identifier):
        utc_now = datetime.now(timezone.utc)
        is_good_standing = test_status in ( 'SUCCESS_GOOD_STANDING', 'SUCCESS_FLAG_ON_WITH_PERMISSION')
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value,
                        state=Business.State.ACTIVE,
                        founding_date=utc_now,
                        restoration_expiry_date=utc_now if not is_good_standing else None)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)


    mocker.patch.object(flags, 'is_on', return_value=flag_enabled)

    permission_error = None if has_permission else Error(
        HTTPStatus.BAD_REQUEST, [{'message': 'Permission Denied - You do not have permissions to amalgamate business which is not in good standing.'}])
    mocker.patch.object(PermissionService, 'check_user_permission', return_value=permission_error)

    mocker.patch('legal_api.services.filings.validations.common_validations.AccountService.get_contacts', return_value={'contacts': [{'email': 'test@example.com'}]})

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code is None:
        assert not err
    else:
        assert expected_code == err.code
        if isinstance(expected_msg, list):
            assert f'{expected_msg[0]} is not in good standing.' == err.msg[0]['error']
            assert f'{expected_msg[1]} is not in good standing.' == err.msg[1]['error']
        else:
            error_msg = err.msg[0].get('error') or err.msg[0].get('message')
            assert 'Permission Denied - You do not have permissions to amalgamate business which is not in good standing.' == error_msg


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, 'A business with identifier:BC7654321 not found.'),
        ('SUCCESS', None, None)
    ]
)
def test_is_business_not_found(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses not found."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234567'
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC7654321'
        }
    ]

    def mock_find_by_identifier(identifier):
        if test_status == 'FAIL' and identifier == 'BC7654321':
            return None

        return Business(identifier=identifier,
                        founding_date=datetime.fromtimestamp(0, timezone.utc),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    # a business not in LEAR is looked up in COLIN - not there either
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=MockResponse({}, HTTPStatus.NOT_FOUND))

    with jwt_request_context(app, jwt, [BASIC_USER]):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, role, flag_enabled, has_permission, expected_code, expected_msg',
    [
        ('FAIL_FLAG_OFF', BASIC_USER, False, False, HTTPStatus.BAD_REQUEST,
         'Foreign Co. foreign corporation cannot be amalgamated except by Registries staff.'),
        ('SUCCESS', STAFF_ROLE, False, False, None, None),
        ('FAIL_FLAG_ON_NO_PERMISSION', BASIC_USER, True, False, HTTPStatus.BAD_REQUEST,
         'Permission Denied - You do not have permissions to amalgamate a foreign corporation.'),
        ('SUCCESS_FLAG_ON_WITH_PERMISSION', BASIC_USER, True, True, None, None)
    ]
)
def test_amalgamating_foreign_business(mocker, app, session, jwt, test_status, role, flag_enabled, has_permission, expected_code, expected_msg):
    """Assert valid amalgamating foreign business."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        founding_date=datetime.fromtimestamp(0, tz=timezone.utc),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch.object(flags, 'is_on', return_value=flag_enabled)

    permission_error = None if has_permission else Error(
        HTTPStatus.BAD_REQUEST, [{'message': 'Permission Denied - You do not have permissions to amalgamate a foreign corporation.'}])
    mocker.patch.object(PermissionService, 'check_user_permission', return_value=permission_error)
    
    mocker.patch('legal_api.services.filings.validations.common_validations.AccountService.get_contacts', return_value={'contacts': [{'email': 'test@example.com'}]})

    with jwt_request_context(app, jwt, [role], 'test-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code is None:
        assert not err
    else:
        assert expected_code == err.code
        error_msg = err.msg[0].get('error') or err.msg[0].get('message')
        assert expected_msg == error_msg


@pytest.mark.parametrize(
    'test_status, role, expected_code, expected_msg',
    [
        ('FAIL', STAFF_ROLE, HTTPStatus.BAD_REQUEST,
         'Foreign Co. foreign corporation must not amalgamate with a BC company to form a BC Unlimited Liability Company.'),
        ('SUCCESS', STAFF_ROLE, None, None)
    ]
)
def test_amalgamating_foreign_business_with_bc_company_to_ulc(mocker, app, session, jwt,
                                                              test_status, role, expected_code, expected_msg):
    """Assert valid amalgamating foreign business with bc company to form ulc."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    if test_status == 'FAIL':
        filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = 'ULC'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [role], 'test-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, role, expected_code, expected_msg',
    [
        ('FAIL', STAFF_ROLE, HTTPStatus.BAD_REQUEST,
         'A BC Unlimited Liability Company cannot amalgamate with a foreign company Foreign Co..'),
        ('SUCCESS', STAFF_ROLE, None, None)
    ]
)
def test_amalgamating_foreign_business_with_ulc_company(mocker, app, session, jwt,
                                                        test_status, role, expected_code, expected_msg):
    """Assert valid amalgamating foreign business with ulc company."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BC_ULC_COMPANY.value
                        if test_status == 'FAIL' else Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [role], 'test-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST,
         'A BC Community Contribution Company must amalgamate to form a new BC Community Contribution Company.'),
        ('SUCCESS', None, None)
    ]
)
def test_amalgamating_cc_to_cc(mocker, app, session, jwt,
                               test_status, expected_code, expected_msg):
    """Assert valid amalgamating cc to cc."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = 'CC'
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value
                        if test_status == 'FAIL' else Business.LegalTypes.BC_CCC.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'test_status, legal_type',
    [
        ('FAIL', Business.LegalTypes.BC_CCC.value),
        ('SUCCESS_CC', Business.LegalTypes.BC_CCC.value),
        ('FAIL', Business.LegalTypes.BC_ULC_COMPANY.value),
        ('SUCCESS_ULC', Business.LegalTypes.BC_ULC_COMPANY.value)
    ]
)
def test_amalgamating_expro_to_cc_or_ulc(mocker, app, session, jwt, test_status, legal_type):
    """Assert valid amalgamating expro with bc company to cc or ulc."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234567'
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'legalName': 'Foreign Co.',
            'foreignJurisdiction': {
                'country': 'CA',
                'region': 'BC'
            },
            'identifier': 'A1234567' if test_status == 'FAIL' else '7654321'
        }
    ]

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BC_CCC.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    expected_msg = 'An extra-Pro cannot amalgamate with anything to become a BC Unlimited Liability Company or a BC Community Contribution Company.'
    if test_status == 'SUCCESS_CC':
        assert not err
    elif test_status == 'SUCCESS_ULC':
        assert not next((x for x in err.msg if x['error'] == expected_msg), None)
    else:
        assert HTTPStatus.BAD_REQUEST == err.code
        assert next((x for x in err.msg if x['error'] == expected_msg), None)


@pytest.mark.parametrize(
    'test_status, legal_type',
    [
        ('FAIL', Business.LegalTypes.COMP.value),
        ('SUCCESS', Business.LegalTypes.BCOMP.value),
    ]
)
def test_regular_amalgamation_adoptable_name(mocker, app, session, jwt, test_status, legal_type):
    """Assert valid regular amalgamation adoptable name."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    adoptable_name = f'Test adoptable name {legal_type}'
    filing['filing']['amalgamationApplication']['nameRequest']['legalName'] = adoptable_name
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234567'
        },
        {
            'role': AmalgamatingBusiness.Role.amalgamating.name,
            'identifier': 'BC1234568'
        }
    ]

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_name=adoptable_name,
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert HTTPStatus.BAD_REQUEST == err.code
        assert err.msg[0]['error'] == 'Adopt a name that have the same business type as the resulting business.'


@pytest.mark.parametrize(
    'test_status, amalgamating_businesses, expected_code, expected_msg',
    [
        ('FAIL_BC', [
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'legalName': 'Foreign Co.',
             'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}, 'identifier': '123456'}
        ], HTTPStatus.BAD_REQUEST, 'Duplicate amalgamating business entry found in list: BC1234567.'),
        ('FAIL_EXPRO', [
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'legalName': 'Foreign Co.',
             'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}, 'identifier': '123456'},
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'legalName': 'Foreign Co.',
             'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}, 'identifier': '123456'}
        ], HTTPStatus.BAD_REQUEST, 'Duplicate amalgamating business entry found in list: 123456.'),
        ('SUCCESS', [
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
            {'role': AmalgamatingBusiness.Role.amalgamating.name, 'legalName': 'Foreign Co.',
             'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}, 'identifier': '123456'}
        ], None, None)
    ]
)
def test_duplicate_amalgamating_businesses(mocker, app, session, jwt, test_status, amalgamating_businesses,
                                           expected_code, expected_msg):
    """Assert duplicate amalgamating businesses."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = amalgamating_businesses

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']


@pytest.mark.parametrize(
    'amalgamation_type, amalgamating_businesses, expected_code, expected_msg',
    [
        (Amalgamation.AmalgamationTypes.regular.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234568'}],
         None, None),
        (Amalgamation.AmalgamationTypes.regular.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'}],
         HTTPStatus.BAD_REQUEST,
         'Regular amalgamation must have 2 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.regular.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': 'BC1234568'},
          {'role': AmalgamatingBusiness.Role.primary.name, 'identifier': 'BC1234569'}],
         HTTPStatus.BAD_REQUEST,
         'Regular amalgamation must have 2 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.vertical.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': 'BC1234568'}],
         None, None),
        (Amalgamation.AmalgamationTypes.vertical.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234568'}],
         HTTPStatus.BAD_REQUEST,
         'Vertical amalgamation must have a holding and 1 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.vertical.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.primary.name, 'identifier': 'BC1234568'}],
         HTTPStatus.BAD_REQUEST,
         'Vertical amalgamation must have a holding and 1 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.horizontal.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.primary.name, 'identifier': 'BC1234568'}],
         None, None),
        (Amalgamation.AmalgamationTypes.horizontal.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234568'}],
         HTTPStatus.BAD_REQUEST,
         'Horizontal amalgamation must have a primary and 1 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.horizontal.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': 'BC1234568'}],
         HTTPStatus.BAD_REQUEST,
         'Horizontal amalgamation must have a primary and 1 or more amalgamating businesses.'),
        (Amalgamation.AmalgamationTypes.horizontal.name,
         [{'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
          {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': '1234568',
           'legalName': 'Foreign Co.', 'foreignJurisdiction': {'country': 'CA', 'region': 'AB'}}],
         HTTPStatus.BAD_REQUEST,
         'A Foreign Co. foreign corporation cannot be marked as Primary or Holding.')
    ]
)
def test_amalgamating_business_roles(mocker, app, session, jwt, amalgamation_type,
                                     amalgamating_businesses, expected_code, expected_msg):
    """Assert amalgamating business roles are valid."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    if amalgamation_type == Amalgamation.AmalgamationTypes.regular.name:
        filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = amalgamating_businesses

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.COMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_primary_or_holding_match',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'legal_type, mock_legal_type, amalgamation_type, expected_code',
    [
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value,
         Amalgamation.AmalgamationTypes.vertical.name, HTTPStatus.BAD_REQUEST),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.COMP.value,
         Amalgamation.AmalgamationTypes.horizontal.name, HTTPStatus.BAD_REQUEST),
        (Business.LegalTypes.COMP.value, Business.LegalTypes.COMP.value,
         Amalgamation.AmalgamationTypes.vertical.name, None),
        (Business.LegalTypes.COMP.value, Business.LegalTypes.COMP.value,
         Amalgamation.AmalgamationTypes.horizontal.name, None),
        (Business.LegalTypes.COMP.value, Business.LegalTypes.CONTINUE_IN.value,
         Amalgamation.AmalgamationTypes.horizontal.name, None),
        (Business.LegalTypes.BCOMP.value, Business.LegalTypes.BCOMP_CONTINUE_IN.value,
         Amalgamation.AmalgamationTypes.horizontal.name, None),
        (Business.LegalTypes.BC_ULC_COMPANY.value, Business.LegalTypes.ULC_CONTINUE_IN.value,
         Amalgamation.AmalgamationTypes.horizontal.name, None)
    ]
)
def test_amalgamation_legal_type_mismatch(mocker, app, session, jwt, legal_type, mock_legal_type,
                                           amalgamation_type, expected_code):
    """Assert amalgamation legal type validation for short form."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'identifier': 'BC1234567', 'role': AmalgamatingBusiness.Role.amalgamating.name},
        {'identifier': 'BC1234568', 'role': (AmalgamatingBusiness.Role.holding.name
                                             if amalgamation_type == Amalgamation.AmalgamationTypes.vertical.name
                                             else AmalgamatingBusiness.Role.primary.name)}]

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=mock_legal_type)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_primary_or_holding_match',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code:
        assert expected_code == err.code
        assert err.msg[0]['error'] == 'Legal type should be same as the legal type in primary or holding business.'
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, expected_code, expected_msg',
    [
        ('FAIL_FOREIGN', HTTPStatus.BAD_REQUEST,
            'A foreign corporation or extra-Pro cannot be part of a Horizontal amalgamation.'),
        ('FAIL_EXPRO', HTTPStatus.BAD_REQUEST,
            'A foreign corporation or extra-Pro cannot be part of a Horizontal amalgamation.')
    ]
)
def test_horizontal_amalgamation(mocker, app, session, jwt, test_name, expected_code, expected_msg):
    """Assert horizontal amalgamation are valid."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['type'] = Amalgamation.AmalgamationTypes.horizontal.name
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'][0]['role'] = \
        AmalgamatingBusiness.Role.primary.name
    if test_name == 'FAIL_EXPRO':
        filing['filing']['amalgamationApplication']['amalgamatingBusinesses'][1]['foreignJurisdiction']['region'] = 'BC'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.COMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_primary_or_holding_match',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    # validate outcomes
    if expected_code:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'amalgamation_type, legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        (Amalgamation.AmalgamationTypes.regular.name, Business.LegalTypes.BCOMP.value, False, True, False),
        (Amalgamation.AmalgamationTypes.regular.name, Business.LegalTypes.BCOMP.value, False, False, True),
        (Amalgamation.AmalgamationTypes.regular.name, Business.LegalTypes.BCOMP.value, True, True, True),
        (Amalgamation.AmalgamationTypes.regular.name, Business.LegalTypes.BCOMP.value, True, False, True),

        # structural share checks apply to short-form too - inherited bad data must be fixed at the source
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, False, True, False),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, False, False, True),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, True, True, True),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, True, False, True),

        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, False, True, False),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, False, False, True),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, True, True, True),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, True, False, True),
    ]
)
def test_amalgamation_share_class_series_validation(mocker, app, session, jwt, amalgamation_type, legal_type,
                                                    has_rights_or_restrictions, has_series, should_pass):
    """Test share class/series validation in amalgamation application with different amalgamation types."""
    filing = {'filing': {}}
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type

    if 'shareStructure' in filing['filing']['amalgamationApplication']:
        for share_class in filing['filing']['amalgamationApplication']['shareStructure']['shareClasses']:
            share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
            if not has_rights_or_restrictions:
                if not has_series:
                    share_class.pop('series', None)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])

    err = validate(None, filing)

    if should_pass:
        assert err is None
    else:
        assert err
        assert any('cannot have series when hasRightsOrRestrictions is false' in msg['error'] for msg in err.msg)

# setup
now = date(2020, 9, 17)

@pytest.mark.parametrize(
    'amalgamation_type',
    [
        Amalgamation.AmalgamationTypes.regular.name,
        Amalgamation.AmalgamationTypes.horizontal.name,
        Amalgamation.AmalgamationTypes.vertical.name,
    ]
)
@pytest.mark.parametrize(
    'test_name, effective_date, expected_code, expected_msg',
    [
        ('SUCCESS', '2020-09-18T00:00:00+00:00', None, None),
        ('SUCCESS', None, None, None),
        ('FAIL_INVALID_DATE_TIME_FORMAT', '2020-09-44T00:00:00z',
            HTTPStatus.UNPROCESSABLE_CONTENT, [
                {
                    'path': 'filing/header/effectiveDate',
                    'error': "'2020-09-44T00:00:00z' is not a 'date-time'",
                    'context': []
                },
                {
                    'path': 'filing/header/effectiveDate',
                    'error': "'2020-09-44T00:00:00z' is not a 'date-time'",
                    'context': []
                }]),
        ('FAIL_INVALID_DATE_TIME_MINIMUM', '2020-09-17T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a minimum of 2 minutes ahead.',
                'path': '/filing/header/effectiveDate'
            }]),
        ('FAIL_INVALID_DATE_TIME_MAXIMUM', '2020-09-27T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a maximum of 10 days ahead.',
                'path': '/filing/header/effectiveDate'
            }])
    ]
)
def test_validate_amalgamation_effective_date(
        mocker, session, amalgamation_type, test_name,
        effective_date, expected_code, expected_msg):
    """Test effective date validation in amalgamation application with different amalgamation types."""
    filing = {'filing': {}}
    filing['filing']['header'] = {
        'name': 'amalgamationApplication',
        'date': '2019-04-08',
        'certifiedBy': 'full name',
        'authorizationReceived': True,
        'email': 'no_one@never.get',
        'filingId': 1
    }
    filing['filing']['business'] = {'identifier': 'T1234567'}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = Business.LegalTypes.BCOMP.value
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type

    if effective_date is not None:
        filing['filing']['header']['effectiveDate'] = effective_date

    if 'courtOrder' in filing['filing']['amalgamationApplication']:
        del filing['filing']['amalgamationApplication']['courtOrder']    

    # mock validations
    mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_name_request',
        return_value=[]
    )
    mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
        return_value=[]
    )

    # perform test
    with freeze_time(now):
        err = validate(None, filing)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, flag_enabled, permission_error, expected_code, expected_msg',
    [
        ('SUCCESS_FLAG_ON', True, None, None, None),
        ('SUCCESS_FLAG_OFF', False, None, None, None),
        ('FAIL_PERMISSION_ERROR', True, Error(HTTPStatus.FORBIDDEN, [{'error': 'Permission denied.'}]),
            HTTPStatus.FORBIDDEN, 'Permission denied.'),
    ]
)
def test_amalgamation_permission_and_completing_party_flag(mocker, app, session, test_name, flag_enabled, permission_error, expected_code, expected_msg):
    """Test validate_permission_and_completing_party is called when flag is enabled."""
    account_id = '123456'
    filing = {'filing': {}}
    filing['filing']['header'] = {
        'name': 'amalgamationApplication',
        'date': '2019-04-08',
        'certifiedBy': 'fname mname lname',
        'authorizationReceived': True,
        'email': 'test@email.com',
        'filingId': 1
    }
    filing['filing']['business'] = {'identifier': 'T1234567'}

    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = Business.LegalTypes.BCOMP.value
    filing['filing']['amalgamationApplication']['type'] = Amalgamation.AmalgamationTypes.regular.name

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_party', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_parties_names', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_parties_addresses', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_offices', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_offices_addresses', return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamation_court_order', return_value=[])

    mocker.patch.object(flags, 'is_on', return_value=flag_enabled)
    mock_validate_permission = mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_permission_and_completing_party', return_value=permission_error)
    
    with app.test_request_context(headers={'account-id': account_id}):
        err = validate(None, filing, account_id)

    if flag_enabled:
        mock_validate_permission.assert_called_once()
        call_args = mock_validate_permission.call_args
        assert call_args[0][0] is None 
        assert call_args[0][1] == filing 
        assert call_args[0][2] == 'amalgamationApplication' 
        check_options = call_args[0][4] 

        assert check_options.get('check_name') is False
        assert check_options.get('check_email') is True
        assert check_options.get('check_address') is False
        assert check_options.get('check_document_email') is True
    else:
        # When flag is off
        mock_validate_permission.assert_not_called()
    if expected_code:
        assert err is not None
        assert err.code == expected_code
        assert expected_msg in str(err.msg[0].get('message', err.msg[0].get('error', '')))
    else:
        assert err is None
 

# ---- COLIN amalgamating businesses (corps not loaded in LEAR) ----

COLIN_IDENTIFIER = 'BC0870226'


def _mock_colin_snapshot_response(status_code=HTTPStatus.OK, **overrides):
    """Return a mocked colin-api snapshot response, business fields overridable."""
    business = {
        'identifier': COLIN_IDENTIFIER,
        'legalName': 'COLIN TEST COMPANY LTD.',
        'legalType': Business.LegalTypes.COMP.value,
        'state': Business.State.ACTIVE.name,
        'goodStanding': True,
        'adminFreeze': False,
        'foundingDate': '2000-01-01T08:00:00+00:00',
        'taxId': '791861078BC0001',
        'hasFutureEffectiveFiling': False
    }
    business.update(overrides)
    return MockResponse({'business': business}, status_code)


def _setup_colin_amalgamation_mocks(mocker, affiliated=True):
    """Wire the standard mocks: one LEAR TING plus one identifier not in LEAR."""
    def mock_find_by_identifier(identifier):
        if identifier == COLIN_IDENTIFIER:
            return None
        return Business(identifier=identifier,
                        founding_date=datetime.now(timezone.utc),
                        state=Business.State.ACTIVE,
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 side_effect=lambda identifier, account_id: affiliated or identifier != COLIN_IDENTIFIER)


@pytest.mark.parametrize(
    'test_status, expected_msg',
    [
        ('SUCCESS', None),
        ('HISTORICAL', f'Cannot amalgamate with {COLIN_IDENTIFIER} which is in historical state.'),
        ('FUTURE_EFFECTIVE', f'{COLIN_IDENTIFIER} has a draft, pending or future effective filing.'),
        ('FROZEN', f'{COLIN_IDENTIFIER} is frozen.'),
        ('NOT_AFFILIATED', f'{COLIN_IDENTIFIER} is not affiliated with the currently '
                           'selected BC Registries account.'),
        ('NOT_GOOD_STANDING', f'{COLIN_IDENTIFIER} is not in good standing.'),
        ('GOOD_STANDING_UNKNOWN', f'{COLIN_IDENTIFIER} is not in good standing.'),
        ('OUT_OF_SCOPE_TYPE', f'A business with identifier:{COLIN_IDENTIFIER} not found.'),
        ('COLIN_404', f'A business with identifier:{COLIN_IDENTIFIER} not found.'),
        ('COLIN_500', f'Unable to verify {COLIN_IDENTIFIER} - COLIN is unavailable, try again.'),
        ('COLIN_DOWN', f'Unable to verify {COLIN_IDENTIFIER} - COLIN is unavailable, try again.'),
    ]
)
def test_colin_amalgamating_business(mocker, app, session, jwt, test_status, expected_msg):
    """Assert a COLIN BC/ULC/CC corp not loaded in LEAR is validated from its snapshot."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': COLIN_IDENTIFIER}
    ]

    _setup_colin_amalgamation_mocks(mocker, affiliated=test_status != 'NOT_AFFILIATED')

    snapshot_responses = {
        'HISTORICAL': _mock_colin_snapshot_response(state=Business.State.HISTORICAL.name),
        'FUTURE_EFFECTIVE': _mock_colin_snapshot_response(hasFutureEffectiveFiling=True),
        'FROZEN': _mock_colin_snapshot_response(adminFreeze=True),
        'NOT_GOOD_STANDING': _mock_colin_snapshot_response(goodStanding=False),
        'GOOD_STANDING_UNKNOWN': _mock_colin_snapshot_response(goodStanding=None),
        'OUT_OF_SCOPE_TYPE': _mock_colin_snapshot_response(legalType='CP'),
        'COLIN_404': MockResponse({'message': 'not found'}, HTTPStatus.NOT_FOUND),
        'COLIN_500': MockResponse({}, HTTPStatus.INTERNAL_SERVER_ERROR),
        'COLIN_DOWN': None,
    }
    get_snapshot = mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
        return_value=snapshot_responses.get(test_status, _mock_colin_snapshot_response()))

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    get_snapshot.assert_called_once_with(COLIN_IDENTIFIER)

    if expected_msg is None:
        assert not err
    else:
        assert err.code == HTTPStatus.BAD_REQUEST
        assert expected_msg == err.msg[0]['error']


def test_colin_amalgamating_business_staff_skips_account_checks(mocker, app, session, jwt):
    """Assert staff can amalgamate an unaffiliated, not-in-good-standing COLIN corp."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': COLIN_IDENTIFIER}
    ]

    _setup_colin_amalgamation_mocks(mocker, affiliated=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=_mock_colin_snapshot_response(goodStanding=False))

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    assert not err


def test_colin_amalgamating_business_multiple_tings(mocker, app, session, jwt):
    """Assert each COLIN TING is fetched once and validated from its own snapshot."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': COLIN_IDENTIFIER},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC0870227'}
    ]

    def mock_find_by_identifier(identifier):
        return None

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('business_model.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    get_snapshot = mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
        side_effect=[_mock_colin_snapshot_response(),
                     _mock_colin_snapshot_response(identifier='BC0870227')])

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    assert not err
    assert [call.args[0] for call in get_snapshot.call_args_list] == [COLIN_IDENTIFIER, 'BC0870227']


def test_colin_ccc_ting_satisfies_ccc_rule(mocker, app, session, jwt):
    """Assert a COLIN CC TING counts for the resulting-CC rule."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = Business.LegalTypes.BC_CCC.value
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': COLIN_IDENTIFIER}
    ]

    _setup_colin_amalgamation_mocks(mocker)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=_mock_colin_snapshot_response(legalType=Business.LegalTypes.BC_CCC.value))

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    assert not err


def test_colin_ting_name_is_adoptable(mocker, app, session, jwt):
    """Assert a regular amalgamation can adopt the name of a COLIN TING of the same type."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest'] = {
        'legalType': Business.LegalTypes.COMP.value,
        'legalName': 'COLIN TEST COMPANY LTD.'
    }
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': COLIN_IDENTIFIER}
    ]

    _setup_colin_amalgamation_mocks(mocker)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=_mock_colin_snapshot_response())

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    assert not err


@pytest.mark.parametrize(
    'resulting_legal_type, expect_error',
    [
        (Business.LegalTypes.COMP.value, False),
        (Business.LegalTypes.BCOMP.value, True)
    ]
)
def test_colin_holding_business_legal_type_match(mocker, app, session, jwt, resulting_legal_type, expect_error):
    """Assert the short-form legal-type match runs against a COLIN holding business."""
    account_id = '123456'
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['type'] = Amalgamation.AmalgamationTypes.vertical.name
    filing['filing']['amalgamationApplication']['nameRequest'] = {'legalType': resulting_legal_type}
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': COLIN_IDENTIFIER},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'}
    ]

    _setup_colin_amalgamation_mocks(mocker)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=_mock_colin_snapshot_response())
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_primary_or_holding_match',
                 return_value=[])

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    type_error = 'Legal type should be same as the legal type in primary or holding business.'
    if expect_error:
        assert type_error in [x['error'] for x in err.msg]
    else:
        assert not err


REFRESH_HINT = "Refresh the draft with the business's current data."
SOURCE_UPDATE_HINT = ('This data comes from the holding business - its information must be '
                      'corrected outside of this filing before this amalgamation can be filed.')


def _factory_short_form_source_business(identifier='BC7654321', share_class_name='Class A Shares'):
    """Create a holding/primary business with offices, a director, shares and a resolution."""
    business = factory_business(identifier, entity_type=Business.LegalTypes.COMP.value)
    for office_type in ['registeredOffice', 'recordsOffice']:
        office = Office(office_type=office_type)
        for address_type in [Address.MAILING, Address.DELIVERY]:
            office.addresses.append(Address(city='Victoria', street=f'{identifier} {office_type} {address_type} St',
                                            postal_code='V1V 1V1', country='CA', region='BC',
                                            address_type=address_type))
        business.offices.append(office)

    share_class = ShareClass(name=share_class_name, priority=1, max_share_flag=True, max_shares=1000,
                             par_value_flag=True, par_value=0.85, currency='CAD', special_rights_flag=True,
                             business_id=business.id)
    share_class.series.append(ShareSeries(name='Series A1 Shares', priority=1, max_share_flag=True,
                                          max_shares=500, special_rights_flag=False))
    share_class.save()

    business.resolutions.append(Resolution(resolution_date=date(2020, 5, 13),
                                           resolution_type=Resolution.ResolutionType.SPECIAL.value))

    party = Party(first_name='DIRECTOR', last_name='ONE', party_type=Party.PartyTypes.PERSON.value)
    party.delivery_address = factory_address(f'{identifier} director street', 'delivery')
    party.save()
    business.party_roles.append(PartyRole(role=PartyRole.RoleTypes.DIRECTOR.value,
                                          appointment_date=datetime(2020, 1, 1),
                                          party_id=party.id))
    business.save()
    return business


def _without_nones(value):
    """Drop None-valued keys - model json emits them where the filing schema wants the key absent."""
    if isinstance(value, dict):
        return {k: _without_nones(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_nones(v) for v in value]
    return value


def _short_form_filing_from_lear(business):
    """Return a vertical amalgamation filing populated with the holding business's current data."""
    filing = _get_amalg_template()
    aml = filing['filing']['amalgamationApplication']
    aml['type'] = Amalgamation.AmalgamationTypes.vertical.name
    aml['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': business.identifier},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1111111'}
    ]
    aml['nameRequest'] = {'legalType': business.legal_type, 'legalName': business.legal_name}
    aml['offices'] = _without_nones({
        office.office_type: {f'{address.address_type}Address': address.json for address in office.addresses}
        for office in business.offices.all()
    })
    # no scrub here - the share class schema requires parValue/currency present even when null
    aml['shareStructure'] = {
        'shareClasses': [share_class.json for share_class in business.share_classes.all()],
        'resolutionDates': [resolution.resolution_date.isoformat() for resolution in business.resolutions]
    }

    completing_party = copy.deepcopy(AMALGAMATION_APPLICATION['parties'][0])
    completing_party['roles'] = [role for role in completing_party['roles']
                                 if role['roleType'] == 'Completing Party']
    directors = []
    for party_role in PartyRole.get_active_directors(business.id, date.today()):
        director = party_role.json
        director['roles'] = [{'roleType': 'Director', 'appointmentDate': director.pop('appointmentDate')}]
        director.pop('role', None)
        directors.append(director)
    aml['parties'] = _without_nones([completing_party] + directors)
    return filing


@pytest.mark.parametrize(
    'test_status, expected_msg',
    [
        ('SUCCESS', None),
        ('STALE_LEGAL_NAME', f'Legal name does not match the holding business. {REFRESH_HINT}'),
        ('STALE_OFFICE', f"Offices do not match the holding business's current offices. {REFRESH_HINT}"),
        ('STALE_SHARES',
         f"Share structure does not match the holding business's current share structure. {REFRESH_HINT}"),
        ('STALE_DIRECTORS', f"Directors do not match the holding business's current directors. {REFRESH_HINT}"),
        ('STALE_RESOLUTIONS',
         f"Resolution dates do not match the holding business's current resolution dates. {REFRESH_HINT}"),
    ]
)
def test_short_form_match_lear(app, session, jwt, test_status, expected_msg):
    """Assert a short-form filing must carry the LEAR holding business's current data."""
    account_id = '123456'
    holding = _factory_short_form_source_business()
    factory_business('BC1111111', entity_type=Business.LegalTypes.COMP.value)
    filing = _short_form_filing_from_lear(holding)
    aml = filing['filing']['amalgamationApplication']

    if test_status == 'STALE_LEGAL_NAME':
        aml['nameRequest']['legalName'] = 'A NAME THE BUSINESS NO LONGER HAS LTD.'
    elif test_status == 'STALE_OFFICE':
        aml['offices']['registeredOffice']['deliveryAddress']['streetAddress'] = 'a street they moved away from'
    elif test_status == 'STALE_SHARES':
        aml['shareStructure']['shareClasses'][0]['parValue'] = 99.99
    elif test_status == 'STALE_DIRECTORS':
        aml['parties'] = [party for party in aml['parties']
                          if not any(role['roleType'] == 'Director' for role in party['roles'])]
    elif test_status == 'STALE_RESOLUTIONS':
        aml['shareStructure']['resolutionDates'] = []

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    if test_status == 'SUCCESS':
        assert not err, err.msg
    else:
        assert expected_msg in [x['error'] for x in err.msg]


def test_short_form_match_lear_ignores_db_artifacts(app, session, jwt):
    """Assert ids, priorities and numeric formatting differences do not fail the match."""
    account_id = '123456'
    holding = _factory_short_form_source_business()
    factory_business('BC1111111', entity_type=Business.LegalTypes.COMP.value)
    filing = _short_form_filing_from_lear(holding)
    aml = filing['filing']['amalgamationApplication']

    # the UI round-trips values the comparator must not be sensitive to
    aml['offices']['registeredOffice']['deliveryAddress'].pop('id', None)
    aml['shareStructure']['shareClasses'][0].pop('id', None)
    aml['shareStructure']['shareClasses'][0]['priority'] = 42
    aml['shareStructure']['shareClasses'][0]['parValue'] = 0.850

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    assert not err


def test_short_form_missing_sections(app, session, jwt):
    """Assert a short-form filing without the adopted data sections is rejected."""
    account_id = '123456'
    holding = _factory_short_form_source_business()
    factory_business('BC1111111', entity_type=Business.LegalTypes.COMP.value)
    filing = _short_form_filing_from_lear(holding)
    aml = filing['filing']['amalgamationApplication']
    del aml['offices']
    del aml['shareStructure']
    del aml['nameRequest']['legalName']

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    errors = [x['error'] for x in err.msg]
    assert 'Legal name of the holding business is required for a short-form amalgamation.' in errors
    assert 'Offices of the holding business are required for a short-form amalgamation.' in errors
    assert 'Share structure of the holding business is required for a short-form amalgamation.' in errors


def test_short_form_structural_error_names_the_source(app, session, jwt):
    """Assert an inherited structural problem points the user at the source business."""
    account_id = '123456'
    # a legacy share class name that predates the ' Shares' suffix rule
    holding = _factory_short_form_source_business(share_class_name='Class A Common')
    factory_business('BC1111111', entity_type=Business.LegalTypes.COMP.value)
    filing = _short_form_filing_from_lear(holding)

    with jwt_request_context(app, jwt, [STAFF_ROLE], 'staff-user', account_id):
        err = validate(None, filing, account_id)

    structural_error = next(x['error'] for x in err.msg if "must end with ' Shares'" in x['error'])
    # the data matches the holding business, so the fix lives there - not in this filing
    assert SOURCE_UPDATE_HINT in structural_error
    assert not any('does not match' in x['error'] for x in err.msg)


def _full_colin_snapshot():
    """Return a complete colin snapshot - business plus the sections the match validation reads."""
    address = {'id': 1, 'streetAddress': '123 Colin St', 'streetAddressAdditional': None,
               'addressCity': 'Victoria', 'addressRegion': 'BC', 'addressCountry': 'CA',
               'postalCode': 'V1V 1V1', 'deliveryInstructions': None}
    return {
        **_mock_colin_snapshot_response().json(),
        'parties': [{
            'officer': {'firstName': 'COLIN', 'middleInitial': '', 'lastName': 'DIRECTOR',
                        'organizationName': ''},
            'deliveryAddress': dict(address),
            'mailingAddress': dict(address),
            'roles': [{'roleType': 'Director'}]
        }],
        'offices': {
            'registeredOffice': {'deliveryAddress': dict(address), 'mailingAddress': dict(address)},
            'recordsOffice': {'deliveryAddress': dict(address), 'mailingAddress': dict(address)}
        },
        'shareClasses': [{
            'id': 100, 'name': 'Class A Shares', 'priority': 100, 'hasMaximumShares': True,
            'maxNumberOfShares': 10000, 'hasParValue': False, 'parValue': None, 'currency': None,
            'currencyAdditional': None, 'hasRightsOrRestrictions': False, 'series': []
        }],
        'resolutions': [{'date': '2010-10-10'}]
    }


@pytest.mark.parametrize('test_status', ['SUCCESS', 'STALE_LEGAL_NAME'])
def test_short_form_match_colin(mocker, app, session, jwt, test_status):
    """Assert the short-form match runs against a COLIN holding business's snapshot."""
    account_id = '123456'
    snapshot = _full_colin_snapshot()

    filing = _get_amalg_template()
    aml = filing['filing']['amalgamationApplication']
    aml['type'] = Amalgamation.AmalgamationTypes.vertical.name
    aml['amalgamatingBusinesses'] = [
        {'role': AmalgamatingBusiness.Role.holding.name, 'identifier': COLIN_IDENTIFIER},
        {'role': AmalgamatingBusiness.Role.amalgamating.name, 'identifier': 'BC1234567'}
    ]
    aml['nameRequest'] = {'legalType': Business.LegalTypes.COMP.value,
                          'legalName': snapshot['business']['legalName']}
    aml['offices'] = _without_nones(snapshot['offices'])
    # no scrub here - the share class schema requires parValue/currency present even when null
    aml['shareStructure'] = {'shareClasses': copy.deepcopy(snapshot['shareClasses']),
                             'resolutionDates': ['2010-10-10']}
    completing_party = copy.deepcopy(AMALGAMATION_APPLICATION['parties'][0])
    completing_party['roles'] = [role for role in completing_party['roles']
                                 if role['roleType'] == 'Completing Party']
    directors = []
    for director in copy.deepcopy(snapshot['parties']):
        # the UI normalizes snapshot parties into filing shape - drop empties, stamp type and role
        director['officer'] = {k: v for k, v in director['officer'].items() if v not in (None, '')}
        director['officer']['partyType'] = 'person'
        director['roles'] = [{'roleType': 'Director', 'appointmentDate': '2010-10-10'}]
        directors.append(director)
    aml['parties'] = _without_nones([completing_party] + directors)

    if test_status == 'STALE_LEGAL_NAME':
        aml['nameRequest']['legalName'] = 'A NAME COLIN DOES NOT HAVE LTD.'

    _setup_colin_amalgamation_mocks(mocker)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.colin.get_snapshot',
                 return_value=MockResponse(snapshot))

    with jwt_request_context(app, jwt, [BASIC_USER], 'basic-user', account_id):
        err = validate(None, filing, account_id)

    if test_status == 'SUCCESS':
        assert not err, err.msg
    else:
        assert f'Legal name does not match the holding business. {REFRESH_HINT}' in [x['error'] for x in err.msg]


def test_regular_amalgamation_skips_short_form_match(mocker, app, session):
    """Assert the primary/holding match validation never runs for a regular amalgamation."""
    filing = _get_amalg_template()
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_amalgamating_businesses',
                 return_value=[])
    match_mock = mocker.patch(
        'legal_api.services.filings.validations.amalgamation_application.validate_primary_or_holding_match',
        return_value=[])

    err = validate(None, filing)

    assert not err
    match_mock.assert_not_called()
