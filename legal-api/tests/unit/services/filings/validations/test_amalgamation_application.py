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
from datetime import date

import pytest
from freezegun import freeze_time
import datetime
from registry_schemas.example_data import AMALGAMATION_APPLICATION

from legal_api.models import AmalgamatingBusiness, Amalgamation, Business, Filing
from legal_api.services import NameXService, STAFF_ROLE, BASIC_USER
from legal_api.services.filings.validations.validation import validate

from tests.unit.services.filings.validations import lists_are_equal


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
            'name': AMALGAMATION_APPLICATION['nameRequest']['legalName'],
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    })


def test_invalid_nr_amalgamation(mocker, app, session):
    """Assert that nr is invalid."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    'amalgamation_type, expected_msg',
    [
        (Amalgamation.AmalgamationTypes.regular.name, 'At least one Director and a Completing Party is required.'),
        (Amalgamation.AmalgamationTypes.vertical.name, 'A Completing Party is required.'),
        (Amalgamation.AmalgamationTypes.horizontal.name, 'A Completing Party is required.'),
    ]
)
def test_invalid_party(mocker, app, session, amalgamation_type, expected_msg):
    """Assert that party is invalid."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)

    filing['filing']['amalgamationApplication']['nameRequest'] = {}
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = legal_type
    filing['filing']['amalgamationApplication']['contactPoint']['email'] = 'no_one@never.get'
    filing['filing']['amalgamationApplication']['contactPoint']['phone'] = '123-456-7890'

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


@pytest.mark.parametrize(
    'test_name, legal_type,'
    'class_name_1,class_has_max_shares,class_max_shares,has_par_value,par_value,currency,'
    'series_name_1,series_has_max_shares,series_max_shares,'
    'class_name_2,series_name_2,'
    'expected_code, expected_msg',
    [
        ('SUCCESS', 'BEN', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BEN', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BEN', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'BEN', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'BEN',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BEN',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BEN',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BEN',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
            HTTPStatus.BAD_REQUEST, [{
                'error':
                'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
                'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
            }]),
        ('SUCCESS', 'BC', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BC', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'BC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'BC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'BC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'ULC', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'ULC', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'ULC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'ULC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'ULC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'ULC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'ULC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'ULC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'CC', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CC', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'CC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'CC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/amalgamationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/amalgamationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/amalgamationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value,
                        state=Business.State.ACTIVE if test_status == 'SUCCESS' else Business.State.HISTORICAL)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.services.bootstrap.AccountService.get_account_by_affiliated_identifier',
                 return_value={'orgs': [{'id': account_id}]} if test_status == 'SUCCESS' else {})

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
        ('FAIL', HTTPStatus.BAD_REQUEST, 'BC1234567 has a draft, pending or future effective filing.'),
        ('SUCCESS', None, None)
    ]
)
def test_has_pending_filing(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses has draft, pending or future effective filing."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.models.business.Business.find_by_identifier',
                 return_value=Business(identifier='BC1234567',
                                       legal_type=Business.LegalTypes.BCOMP.value))
    mocker.patch('legal_api.models.filing.Filing.get_filings_by_status',
                 return_value=[Filing()] if test_status == 'FAIL' else [])

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.models.business.Business.find_by_identifier',
                 return_value=Business(identifier='BC1234567',
                                       legal_type=Business.LegalTypes.BCOMP.value))
    mocker.patch('legal_api.models.business.Business.is_pending_amalgamating_business',
                 return_value=[Filing()] if test_status == 'FAIL' else [])

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
        ('FAIL', HTTPStatus.BAD_REQUEST, ['BC1234567', 'BC7654321']),
        ('SUCCESS', None, None)
    ]
)
def test_is_business_affliated(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses is affliated."""
    account_id = '123456'
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)
    mocker.patch('legal_api.services.bootstrap.AccountService.get_account_by_affiliated_identifier',
                 return_value={'orgs': [{'id': account_id}]} if test_status == 'SUCCESS' else {})

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert (f'{expected_msg[0]} is not affiliated with the currently selected BC Registries account.' ==
                err.msg[0]['error'])
        assert (f'{expected_msg[1]} is not affiliated with the currently selected BC Registries account.' ==
                err.msg[1]['error'])


@pytest.mark.parametrize(
    'test_status, expected_code, expected_msg',
    [
        ('FAIL', HTTPStatus.BAD_REQUEST, ['BC1234567', 'BC7654321']),
        ('SUCCESS', None, None)
    ]
)
def test_is_business_in_good_standing(mocker, app, session, jwt, test_status, expected_code, expected_msg):
    """Assert valid amalgamating businesses is in good standing."""
    account_id = '123456'
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value,
                        state=Business.State.ACTIVE,
                        founding_date=utc_now,
                        restoration_expiry_date=utc_now if test_status == 'FAIL' else None)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

    err = validate(None, filing, account_id)

    # validate outcomes
    if test_status == 'SUCCESS':
        assert not err
    else:
        assert expected_code == err.code
        assert f'{expected_msg[0]} is not in good standing.' == err.msg[0]['error']
        assert f'{expected_msg[1]} is not in good standing.' == err.msg[1]['error']


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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=False)  # Client

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
        ('FAIL', BASIC_USER, HTTPStatus.BAD_REQUEST,
         'Foreign Co. foreign corporation cannot be amalgamated except by Registries staff.'),
        ('SUCCESS', STAFF_ROLE, None, None)
    ]
)
def test_amalgamating_foreign_business(mocker, app, session, jwt, test_status, role, expected_code, expected_msg):
    """Assert valid amalgamating foreign business."""
    account_id = '123456'
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        founding_date=datetime.datetime.utcfromtimestamp(0),
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._is_business_affliated',
                 return_value=True)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    def mock_validate_roles(required_roles):
        if role in required_roles:
            return True
        return False
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', side_effect=mock_validate_roles)

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
         'Foreign Co. foreign corporation must not amalgamate with a BC company to form a BC Unlimited Liability Company.'),
        ('SUCCESS', STAFF_ROLE, None, None)
    ]
)
def test_amalgamating_foreign_business_with_bc_company_to_ulc(mocker, app, session, jwt,
                                                              test_status, role, expected_code, expected_msg):
    """Assert valid amalgamating foreign business with bc company to form ulc."""
    account_id = '123456'
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    def mock_validate_roles(required_roles):
        if role in required_roles:
            return True
        return False
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', side_effect=mock_validate_roles)

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    def mock_validate_roles(required_roles):
        if role in required_roles:
            return True
        return False
    mocker.patch('legal_api.utils.auth.jwt.validate_roles', side_effect=mock_validate_roles)

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = amalgamating_businesses

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.BCOMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type
    filing['filing']['amalgamationApplication']['amalgamatingBusinesses'] = amalgamating_businesses

    def mock_find_by_identifier(identifier):
        return Business(identifier=identifier,
                        legal_type=Business.LegalTypes.COMP.value)

    mocker.patch('legal_api.services.filings.validations.amalgamation_application.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['nrNumber'] = 'NR 1234567'
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
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
    mocker.patch('legal_api.services.filings.validations.amalgamation_application._has_pending_filing',
                 return_value=False)
    mocker.patch('legal_api.models.business.Business.find_by_identifier', side_effect=mock_find_by_identifier)

    mocker.patch('legal_api.utils.auth.jwt.validate_roles', return_value=True)  # Staff

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

        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, False, True, True),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, False, False, True),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, True, True, True),
        (Amalgamation.AmalgamationTypes.horizontal.name, Business.LegalTypes.BCOMP.value, True, False, True),

        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, False, True, True),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, False, False, True),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, True, True, True),
        (Amalgamation.AmalgamationTypes.vertical.name, Business.LegalTypes.BCOMP.value, True, False, True),
    ]
)
def test_amalgamation_share_class_series_validation(mocker, app, session, jwt, amalgamation_type, legal_type,
                                                    has_rights_or_restrictions, has_series, should_pass):
    """Test share class/series validation in amalgamation application with different amalgamation types."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'amalgamationApplication', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
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
        ('FAIL_INVALID_DATE_TIME_FORMAT', '2020-09-18T00:00:00Z',
            HTTPStatus.BAD_REQUEST, [{
                'error': '2020-09-18T00:00:00Z is an invalid ISO format for effectiveDate.',
                'path': '/filing/header/effectiveDate'
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
        'email': 'no_one@never.get',
        'filingId': 1
    }
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
    'amalgamation_type',
    [
        Amalgamation.AmalgamationTypes.regular.name,
        Amalgamation.AmalgamationTypes.horizontal.name,
        Amalgamation.AmalgamationTypes.vertical.name,
    ]
)
@pytest.mark.parametrize('test_name, name_translation, expected_code, expected_msg', [
    ('SUCCESS_NAME_TRANSLATION_EMPTY_ARRAY', [], None, None),
    ('SUCCESS_NAME_TRANSLATION', [{"name": "TEST"}], None, None),
    ('FAIL_EMPTY_NAME_TRANSLATION', [{"name": ""}],  HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/amalgamationApplication/nameTranslations/0/name/'
    }]),
    ('FAIL_WHITESPACE_ONLY_NAME_TRANSLATION', [{"name": "   "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/amalgamationApplication/nameTranslations/0/name/'
    }]),
    ('FAIL_LEADING_AND_TRAILING_WHITESPACE_NAME_TRANSLATION', [{"name": " TEST "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot start or end with whitespace.',
        'path': '/filing/amalgamationApplication/nameTranslations/0/name/'
    }]),
    ('FAIL_MULTIPLE_NAME_TRANSLATION', [{"name": "   "}, {"name": " TEST  "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/amalgamationApplication/nameTranslations/0/name/'
    },
    {
        'error': 'Name translation cannot start or end with whitespace.',
        'path': '/filing/amalgamationApplication/nameTranslations/1/name/'
    }
    ]),
])
def test_validate_amalgamation_name_translation(mocker, session, test_name, amalgamation_type, name_translation, expected_code, expected_msg):
    """Test validate name translation if provided."""
    filing = {'filing': {}}
    filing['filing']['header'] = {
        'name': 'amalgamationApplication',
        'date': '2019-04-08',
        'certifiedBy': 'full name',
        'email': 'no_one@never.get',
        'filingId': 1
    }
    filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing['filing']['amalgamationApplication']['nameRequest']['legalType'] = Business.LegalTypes.BCOMP.value
    filing['filing']['amalgamationApplication']['type'] = amalgamation_type

    if 'courtOrder' in filing['filing']['amalgamationApplication']:
        del filing['filing']['amalgamationApplication']['courtOrder']    

    filing['filing']['amalgamationApplication']['nameTranslations'] = name_translation    

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

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        if err:
            print(err, err.code, err.msg)
        assert err is None
