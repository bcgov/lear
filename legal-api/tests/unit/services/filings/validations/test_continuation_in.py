# Copyright © 2024 Province of British Columbia
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
"""Test suite to ensure Continuation In is validated correctly."""
import copy
from unittest.mock import patch
from http import HTTPStatus

import pytest
from registry_schemas.example_data import CONTINUATION_IN

from legal_api.models import Business
from legal_api.services import NameXService
from legal_api.services.filings.validations.validation import validate
from legal_api.services.filings.validations.continuation_in import validate_business_in_colin, _validate_foreign_jurisdiction
from legal_api.utils.datetime import datetime as dt, timedelta

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
            'name': CONTINUATION_IN['nameRequest']['legalName'],
            'state': 'APPROVED',
            'consumptionDate': ''
        }]
    })


def test_invalid_nr_continuation_in(mocker, app, session):
    """Assert that nr is invalid."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'

    invalid_nr_response = {
        'state': 'INPROGRESS',
        'expirationDate': '',
        'names': [{
            'name': 'legal_name',
            'state': 'INPROGRESS',
            'consumptionDate': ''
        }]
    }
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])
    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(invalid_nr_response)):
        err = validate(None, filing)

    assert err
    assert err.msg[0]['error'] == 'Name Request is not approved.'


@pytest.mark.parametrize(
    'legal_type',
    [
        (Business.LegalTypes.CONTINUE_IN.value),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value),
        (Business.LegalTypes.ULC_CONTINUE_IN.value),
        (Business.LegalTypes.CCC_CONTINUE_IN.value),
    ]
)
def test_invalid_party(mocker, app, session, legal_type):
    """Assert that party is invalid."""
    min_director_count_info = {
        Business.LegalTypes.BCOMP_CONTINUE_IN.value: 1,
        Business.LegalTypes.CONTINUE_IN.value: 1,
        Business.LegalTypes.ULC_CONTINUE_IN.value: 1,
        Business.LegalTypes.CCC_CONTINUE_IN.value: 3
    }
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'

    filing['filing']['continuationIn']['parties'] = []
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)

    assert err

    assert err.msg[0]['error'] == 'Must have a minimum of one completing party.'
    assert err.msg[1]['error'] == f'Must have a minimum of {min_director_count_info[legal_type]} Director.'


@pytest.mark.parametrize(
    'test_name, legal_type, delivery_region, delivery_country, mailing_region, mailing_country, expected_code, expected_msg',
    [
        ('SUCCESS', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.ULC_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.CCC_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('SUCCESS', Business.LegalTypes.CONTINUE_IN.value, 'BC', 'CA', 'BC', 'CA', None, None),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.ULC_CONTINUE_IN.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.CONTINUE_IN.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.CCC_CONTINUE_IN.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'BC', 'CA', 'AB', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.CONTINUE_IN.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.ULC_CONTINUE_IN.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_ALL_ADDRESS_REGIONS', Business.LegalTypes.CCC_CONTINUE_IN.value, 'WA', 'CA', 'WA', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'BC', 'NZ', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressCountry'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.CONTINUE_IN.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.ULC_CONTINUE_IN.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.CCC_CONTINUE_IN.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.CONTINUE_IN.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.ULC_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.CCC_CONTINUE_IN.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_ALL_ADDRESS', Business.LegalTypes.BCOMP_CONTINUE_IN.value, 'AB', 'NZ', 'AB', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/continuationIn/offices/recordsOffice/mailingAddress/addressCountry'}
            ])
    ])
def test_validate_continuation_in_office(session, mocker, test_name, legal_type, delivery_region,
                                         delivery_country, mailing_region, mailing_country, expected_code,
                                         expected_msg):
    """Assert that offices can be validated."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type
    filing['filing']['continuationIn']['contactPoint']['email'] = 'no_one@never.get'
    filing['filing']['continuationIn']['contactPoint']['phone'] = '123-456-7890'

    regoffice = filing['filing']['continuationIn']['offices']['registeredOffice']
    regoffice['deliveryAddress']['addressRegion'] = delivery_region
    regoffice['deliveryAddress']['addressCountry'] = delivery_country
    regoffice['mailingAddress']['addressRegion'] = mailing_region
    regoffice['mailingAddress']['addressCountry'] = mailing_country

    recoffice = filing['filing']['continuationIn']['offices']['recordsOffice']
    recoffice['deliveryAddress']['addressRegion'] = delivery_region
    recoffice['deliveryAddress']['addressCountry'] = delivery_country
    recoffice['mailingAddress']['addressRegion'] = mailing_region
    recoffice['mailingAddress']['addressCountry'] = mailing_country

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
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
        ('SUCCESS', 'CBEN', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CBEN', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CBEN', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'CBEN', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'CBEN',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CBEN',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CBEN',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CBEN',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/continuationIn/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CBEN',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/continuationIn/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CBEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CBEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
            HTTPStatus.BAD_REQUEST, [{
                'error':
                'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
                'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
            }]),
        ('SUCCESS', 'C', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'C', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'C', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'C', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'C',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'C',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'C',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'C',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/continuationIn/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'C',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/continuationIn/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'C',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'C',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'CUL', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CUL', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CUL', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'CUL', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'CUL',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CUL',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CUL',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CUL',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/continuationIn/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CUL',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/continuationIn/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CUL',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CUL',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('SUCCESS', 'CCC', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CCC', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'CCC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'CCC', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2', 'CCC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CCC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/continuationIn/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CCC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CCC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/continuationIn/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CCC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/continuationIn/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CCC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CCC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/continuationIn/shareClasses/0/series/0/maxNumberOfShares'
         }])
    ])
def test_validate_continuation_in_share_classes(session, mocker, test_name, legal_type,
                                                class_name_1, class_has_max_shares, class_max_shares,
                                                has_par_value, par_value, currency, series_name_1, series_has_max_shares,
                                                series_max_shares,
                                                class_name_2, series_name_2,
                                                expected_code, expected_msg):
    """Assert that validator validates share class correctly."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type

    share_structure = filing['filing']['continuationIn']['shareStructure']
    share_structure['shareClasses'].append({
        'id': 2,
        'name': 'Share Class 2',
        'priority': 1,
        'hasMaximumShares': False,
        'maxNumberOfShares': None,
        'hasParValue': False,
        'parValue': None,
        'currency': None,
        'hasRightsOrRestrictions': True,
        'series': []
    })
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

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
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
    'test_status, file_number, effect_of_order, expected_code, expected_msg',
    [
        ('FAIL', '12345678901234567890', 'invalid', HTTPStatus.BAD_REQUEST, 'Invalid effectOfOrder.'),
        ('SUCCESS', '12345678901234567890', 'planOfArrangement', None, None)
    ]
)
def test_continuation_in_court_orders(mocker, app, session,
                                      test_status, file_number, effect_of_order, expected_code, expected_msg):
    """Assert valid court orders."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'

    court_order = {'effectOfOrder': effect_of_order}
    if file_number:
        court_order['fileNumber'] = file_number
    filing['filing']['continuationIn']['courtOrder'] = court_order

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)

    # validate outcomes
    if test_status == 'FAIL':
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'legal_type, expected_msg',
    [
        (Business.LegalTypes.CONTINUE_IN.value, None),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, None),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, None),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, 'Affidavit from the directors is required.'),
    ]
)
def test_continuation_in_foreign_jurisdiction(mocker, app, session, legal_type, expected_msg):
    """Assert valid continuation in foreign business."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type

    del filing['filing']['continuationIn']['foreignJurisdiction']['affidavitFileKey']

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)

    # validate outcomes
    if expected_msg:
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


def test_validate_business_in_colin(mocker, app, session):
    """Assert valid continuation EXPRO business"""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['nameRequest']['legalType'] = 'C'
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=(404, {}))

    err = validate(None, filing)
    assert err.code == HTTPStatus.BAD_REQUEST


def test_validate_business_in_colin_founding_date_mismatch(mocker, app, session):
    """Assert continuation EXPRO business with founding date mismatch."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    
    # Add the EXPRO business data to simulate a mismatch in founding date
    filing['filing']['continuationIn']['business'] = {
        'identifier': 'A0077779',
        'legalName': 'Test Company Inc.',
        'foundingDate': '2009-07-23T07:00:00.000+00:00'
    }

    mocker.patch('legal_api.services.colin.query_business', return_value=mocker.Mock(
        status_code=HTTPStatus.OK,
        json=lambda: {
            'business': {
                'identifier': 'A0077779',
                'legalName': 'Test Company Inc.',
                # Different founding date to trigger validation error
                'foundingDate': '2010-01-01T18:21:13-00:00'
            }
        }
    ))

    err = validate_business_in_colin(filing, 'continuationIn')
    assert err[0]['error'] == 'Founding date does not match with founding date from Colin.'
    assert err[0]['path'] == '/filing/continuationIn/business/foundingDate'


def test_validate_business_in_colin_founding_date_match(mocker, app, session):
    """Assert continuation EXPRO business with matching founding date."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    
    # Add the EXPRO business data with a matching founding date
    filing['filing']['continuationIn']['business'] = {
        'identifier': 'A0077779',
        'legalName': 'Test Company Inc.',
        'foundingDate': '2009-07-23T18:31:24-00:00'
    }

    mocker.patch('legal_api.services.colin.query_business', return_value=mocker.Mock(
        status_code=HTTPStatus.OK,
        json=lambda: {
            'business': {
                'identifier': 'A0077779',
                'legalName': 'Test Company Inc.',
                'foundingDate': '2009-07-23T18:31:24-00:00'
            }
        }
    ))

    err = validate_business_in_colin(filing, 'continuationIn')
    assert len(err) == 0


def test_validate_foreign_jurisdiction_incorporation_date(mocker, app, session):
    """Assert that an error is raised if the incorporation date is set to a future date."""
    # Prepare a filing JSON with a future incorporation date
    future_date = (dt.now() + timedelta(days=1)).isoformat()  # Set date to tomorrow
    filing = {
        'filing': {
            'continuationIn': {
                'foreignJurisdiction': {
                    'country': 'USA',
                    'region': 'WA',
                    'incorporationDate': future_date
                }
            },
            'header': {
                'name': 'continuationIn',
                'date': '2019-04-08',
                'certifiedBy': 'full name',
                'email': 'no_one@never.get',
                'filingId': 1
            }
        }
    }

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_foreign_jurisdiction', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)

    # Run the validation function
    err = _validate_foreign_jurisdiction(filing, 'continuationIn', 'CCC')

    # Assert that the error list contains the appropriate error for future incorporation date
    assert len(err) == 1
    assert err[0]['error'] == 'Incorporation date cannot be in the future.'
    assert err[0]['path'] == '/filing/continuationIn/foreignJurisdiction/incorporationDate'


@pytest.mark.parametrize(
    'test_status, is_approved',
    [
        ('FAIL', True),
        ('SUCCESS', False)
    ]
)
def test_validate_before_and_after_approval(mocker, app, session, test_status, is_approved):
    """Assert not valid if these are ommited when approved."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = is_approved
    del filing['filing']['continuationIn']['offices']
    del filing['filing']['continuationIn']['parties']
    del filing['filing']['continuationIn']['shareStructure']

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)
    if is_approved:
        assert err.code == HTTPStatus.UNPROCESSABLE_ENTITY
    else:
        assert not err


@pytest.mark.parametrize(
    'legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        (Business.LegalTypes.CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.CCC_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.ULC_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, True, False, True),
    ]
)
def test_continuation_in_share_class_series_validation(mocker, app, session, legal_type,
                                                       has_rights_or_restrictions, has_series, should_pass):
    """Test share class/series validation in continuation in application."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type

    if 'shareStructure' in filing['filing']['continuationIn']:
        for share_class in filing['filing']['continuationIn']['shareStructure']['shareClasses']:
            share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
            if not has_rights_or_restrictions:
                if not has_series:
                    share_class.pop('series', None)

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)

    if should_pass:
        assert err is None
    else:
        assert err
        assert any('cannot have series when hasRightsOrRestrictions is false' in msg['error'] for msg in err.msg)


@pytest.mark.parametrize(
    'test_name, has_delivery_address, expected_code, expected_msg',
    [
        ('MISSING_DELIVERY_ADDRESS', False, HTTPStatus.BAD_REQUEST, 'deliveryAddress is required.'),
        ('SUCCESS', True, None, None),
    ]
)
def test_continuation_in_parties_delivery_address_validation(mocker, app, session, test_name, has_delivery_address,
                                                             expected_code, expected_msg):
    """Test parties delivery address validation in continuation in application."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = 'BC'


    if not has_delivery_address:
        if 'deliveryAddress' in filing['filing']['continuationIn']['parties'][0]:
            del filing['filing']['continuationIn']['parties'][0]['deliveryAddress']

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin', return_value=[])

    err = validate(None, filing)

    if expected_code:
        assert err.code == expected_code
        assert any(expected_msg in msg['error'] for msg in err.msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        (Business.LegalTypes.CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.BCOMP_CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.CCC_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.CCC_CONTINUE_IN.value, True, False, True),

        (Business.LegalTypes.ULC_CONTINUE_IN.value, False, True, False),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, False, False, True),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, True, True, True),
        (Business.LegalTypes.ULC_CONTINUE_IN.value, True, False, True),
    ]
)
def test_continuation_in_share_class_series_validation(mocker, app, session, legal_type,
                                                       has_rights_or_restrictions, has_series, should_pass):
    """Test share class/series validation in continuation in application."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type

    if 'shareStructure' in filing['filing']['continuationIn']:
        for share_class in filing['filing']['continuationIn']['shareStructure']['shareClasses']:
            share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
            if not has_rights_or_restrictions:
                if not has_series:
                    share_class.pop('series', None)

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request',
                 return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])

    err = validate(None, filing)

    if should_pass:
        assert err is None
    else:
        assert err
        assert any('cannot have series when hasRightsOrRestrictions is false' in msg['error'] for msg in err.msg)


@pytest.mark.parametrize(
    'test_name, has_delivery_address, expected_code, expected_msg',
    [
        ('MISSING_DELIVERY_ADDRESS', False, HTTPStatus.BAD_REQUEST, 'deliveryAddress is required.'),
        ('SUCCESS', True, None, None),
    ]
)
def test_continuation_in_parties_delivery_address_validation(mocker, app, session, test_name, has_delivery_address,
                                                             expected_code, expected_msg):
    """Test parties delivery address validation in continuation in application."""
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['isApproved'] = True

    filing['filing']['continuationIn']['nameRequest'] = {}
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = 'BC'


    if not has_delivery_address:
        if 'deliveryAddress' in filing['filing']['continuationIn']['parties'][0]:
            del filing['filing']['continuationIn']['parties'][0]['deliveryAddress']

    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_roles', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_name_request', return_value=[])
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin', return_value=[])

    err = validate(None, filing)

    if expected_code:
        assert err.code == expected_code
        assert any(expected_msg in msg['error'] for msg in err.msg)
    else:
        assert err is None

@pytest.mark.parametrize('should_pass, phone_number, extension', [
    (True, '1234567890', 12345),
    (True, '1234567890', 1234),
    (True, '1234567890', 123),
    (True, '1234567890', 12),
    (True, '1234567890', 1),
    (False, '1234567890', 123456),
    (False, '12345678901', 12345),
    (True, '(123)456-7890', None),
    (False, '(1234)456-7890', None),
    (False, '(123)4567-7890', None),
    (False, '(123)456-78901', None),
    (True, '123-456-7890', None),
    (False, '1234-456-7890', None),
    (False, '123-4567-7890', None),
    (False, '123-456-78901', None),
    (True, '123.456.7890', None),
    (False, '1234.456.7890', None),
    (False, '123.4567.7890', None),
    (False, '123.456.78901', None),
    (True, '123 456 7890', None),
    (False, '1234 456 7890', None),
    (False, '123 4567 7890', None),
    (False, '123 456 78901', None),
    (True, None, None)
])
def test_continuation_in_phone_number_validation(mocker, app, session, jwt, should_pass, phone_number, extension):
    """Test validate phone number and / or extension if they are provided."""
    legal_type = Business.LegalTypes.CONTINUE_IN.value
    filing = {'filing': {}}
    filing['filing']['header'] = {'name': 'continuationIn', 'date': '2019-04-08',
                                  'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}
    filing['filing']['continuationIn'] = copy.deepcopy(CONTINUATION_IN)
    filing['filing']['continuationIn']['nameRequest']['nrNumber'] = 'NR 1234567'
    filing['filing']['continuationIn']['nameRequest']['legalType'] = legal_type

    if phone_number:
        filing['filing']['continuationIn']['contactPoint']['phone'] = phone_number
    if extension:
        filing['filing']['continuationIn']['contactPoint']['extension'] = extension

    filing['filing']['continuationIn']['isApproved'] = True
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_pdf', return_value=None)
    mocker.patch('legal_api.services.filings.validations.continuation_in.validate_business_in_colin',
                 return_value=[])
    with patch.object(NameXService, 'query_nr_number', return_value=_mock_nr_response(legal_type)):
        err = validate(None, filing)

    if should_pass:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code    