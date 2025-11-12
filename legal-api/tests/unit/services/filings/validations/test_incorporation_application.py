# Copyright © 2019 Province of British Columbia
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
"""Test suite to ensure the Incorporation Application is validated correctly."""
import copy
from datetime import date
from http import HTTPStatus

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import COURT_ORDER, INCORPORATION, INCORPORATION_FILING_TEMPLATE
from registry_schemas.example_data.schema_data import FILING_HEADER
from reportlab.lib.pagesizes import letter

from legal_api.models import Business
from legal_api.services.filings import validate
from legal_api.services.filings.validations.incorporation_application import validate_coop_parties_mailing_address, validate_parties_names

from tests.unit.services.filings.test_utils import _upload_file

from . import create_party, create_party_address, lists_are_equal, create_officer
from tests import not_github_ci
from unittest.mock import patch
from legal_api.services import NameXService
from tests.unit import MockResponse


# setup
identifier = 'NR 1234567'
legal_name = 'Test 1234567'
now = date(2020, 9, 17)
founding_date = now - datedelta.YEAR
business = Business(identifier=identifier)
effective_date = '2020-09-18T00:00:00+00:00'
court_order_date = '2020-09-17T00:00:00+00:00'
incorporation_application_name = 'incorporationApplication'

nr_response = {
    'state': 'APPROVED',
    'expirationDate': '',
    'names': [{
        'name': legal_name,
        'state': 'APPROVED',
        'consumptionDate': ''
    }]
}


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
                 '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BC_ULC_COMPANY.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.COMP.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_DELIVERY_REGION', Business.LegalTypes.BC_CCC.value, 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'AB', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.COMP.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_NOT_BC_MAILING_REGION', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path':
                  '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
         ]),
        ('FAIL_ALL_ADDRESS_REGIONS', Business.LegalTypes.BC_CCC.value, 'WA', 'CA', 'WA', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BCOMP.value, 'BC', 'NZ', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
            ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.COMP.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_DELIVERY_COUNTRY', Business.LegalTypes.BC_CCC.value, 'BC', 'NZ', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
         ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BCOMP.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.COMP.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BC_ULC_COMPANY.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', Business.LegalTypes.BC_CCC.value, 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_ALL_ADDRESS', Business.LegalTypes.BCOMP.value, 'AB', 'NZ', 'AB', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'},
                {'error': "Address Region must be 'BC'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ])
    ])
def test_validate_incorporation_addresses_basic(session, mocker, test_name, legal_type, delivery_region,
                                                delivery_country, mailing_region, mailing_country, expected_code,
                                                expected_msg):
    """Assert that incorporation offices can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1,
                                       'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['contactPoint']['email'] = 'no_one@never.get'
    filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = '123-456-7890'

    regoffice = filing_json['filing'][incorporation_application_name]['offices']['registeredOffice']
    regoffice['deliveryAddress']['addressRegion'] = delivery_region
    regoffice['deliveryAddress']['addressCountry'] = delivery_country
    regoffice['mailingAddress']['addressRegion'] = mailing_region
    regoffice['mailingAddress']['addressCountry'] = mailing_country

    recoffice = filing_json['filing'][incorporation_application_name]['offices']['recordsOffice']
    recoffice['deliveryAddress']['addressRegion'] = delivery_region
    recoffice['deliveryAddress']['addressCountry'] = delivery_country
    recoffice['mailingAddress']['addressRegion'] = mailing_region
    recoffice['mailingAddress']['addressCountry'] = mailing_country

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_roles',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, expected_code, expected_msg',
    [
        ('SUCCESS', Business.LegalTypes.BCOMP.value, None, None),
        ('SUCCESS', Business.LegalTypes.BC_ULC_COMPANY.value, None, None),
        ('SUCCESS', Business.LegalTypes.BC_CCC.value, None, None),
        ('SUCCESS', Business.LegalTypes.COMP.value, None, None),
        ('FAIL_LEGAL_NAME_MISMATCH', Business.LegalTypes.BCOMP.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal name is not same as the business legal name.',
           'path': '/filing/incorporationApplication/nameRequest/legalName'}]),
        ('FAIL_LEGAL_NAME_MISMATCH', Business.LegalTypes.BC_ULC_COMPANY.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal name is not same as the business legal name.',
           'path': '/filing/incorporationApplication/nameRequest/legalName'}]),
        ('FAIL_LEGAL_NAME_MISMATCH', Business.LegalTypes.BC_CCC.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal name is not same as the business legal name.',
           'path': '/filing/incorporationApplication/nameRequest/legalName'}]),
        ('FAIL_LEGAL_NAME_MISMATCH', Business.LegalTypes.COMP.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal name is not same as the business legal name.',
          'path': '/filing/incorporationApplication/nameRequest/legalName'}]),
        ('FAIL_LEGAL_TYPE_MISMATCH', Business.LegalTypes.BCOMP.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal type is not same as the business legal type.',
           'path': '/filing/incorporationApplication/nameRequest/legalType'}]),
        ('FAIL_LEGAL_TYPE_MISMATCH', Business.LegalTypes.BC_ULC_COMPANY.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal type is not same as the business legal type.',
           'path': '/filing/incorporationApplication/nameRequest/legalType'}]),
        ('FAIL_LEGAL_TYPE_MISMATCH', Business.LegalTypes.BC_CCC.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal type is not same as the business legal type.',
           'path': '/filing/incorporationApplication/nameRequest/legalType'}]),
        ('FAIL_LEGAL_TYPE_MISMATCH', Business.LegalTypes.COMP.value, HTTPStatus.BAD_REQUEST,
         [{'error': 'Name Request legal type is not same as the business legal type.',
           'path': '/filing/incorporationApplication/nameRequest/legalType'}])
    ])
def test_validate_name_request(session, mocker, test_name, legal_type, expected_code, expected_msg):
    """Assert that incorporation name request can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1,
                                       'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    curr_legal_type = legal_type if test_name not in ['FAIL_LEGAL_TYPE_MISMATCH'] else 'CCC'
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = curr_legal_type
    if test_name not in ['FAIL_LEGAL_NAME_MISMATCH']:
        filing_json['filing'][incorporation_application_name]['nameRequest']['legalName'] = legal_name
    else:
        filing_json['filing'][incorporation_application_name]['nameRequest']['legalName'] = 'company name'
    filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = '123-456-7890'
    nr_response_copy = copy.deepcopy(nr_response)
    nr_response_copy['legalType'] = legal_type

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_roles',
                 return_value=[])

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_response_copy)):
        with freeze_time(now):
            err = validate(business, filing_json)
    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, parties, expected_code, expected_msg',
    [
        (
            'SUCCESS', 'BEN',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Incorporator']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']}
            ],
            None, None
        ),
        (
            'SUCCESS', 'BC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Incorporator']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']}
            ],
            None, None
        ),
        (
            'SUCCESS', 'ULC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Incorporator']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']}
            ],
            None, None
        ),
        (
            'SUCCESS', 'CC',
            [
                {'partyName': 'officer1', 'roles': ['Director', 'Completing Party']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']},
                {'partyName': 'officer3', 'roles': ['Director']}
            ],
            None, None
        ),
        (
            'FAIL_UNEXPECTED_PARTY_ROLE', 'BC',
            [
                 {'partyName': 'officer1', 'roles': ['Completing Party', 'Incorporator']},
                 {'partyName': 'officer2', 'roles': ['Incorporator', 'Director', 'Custodian']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Invalid party role(s) provided: Custodian',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_MULTIPLE_INVALID_PARTY_ROLES', 'BC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Incorporator', 'Custodian']},
                {'partyName': 'officer2', 'roles': ['Director', 'Liquidator', 'Proprietor']},
                {'partyName': 'officer3', 'roles': ['Officer', 'Applicant']}
            ],
            HTTPStatus.BAD_REQUEST,
            [{
                'error': 'Invalid party role(s) provided: Applicant, Custodian, Liquidator, Officer, Proprietor',
                'path': '/filing/incorporationApplication/parties/roles'
            }]
        ),
        (
            'FAIL_EXCEEDING_ONE_COMPLETING_PARTY', 'BEN',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Director']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Completing Party']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a maximum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_ATLEAST_ONE_DIRECTOR', 'BEN',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party']},
                {'partyName': 'officer2', 'roles': ['Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of 1 Director',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_ATLEAST_ONE_DIRECTOR', 'BC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party']},
                {'partyName': 'officer2', 'roles': ['Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of 1 Director',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_ATLEAST_ONE_DIRECTOR', 'ULC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party']},
                {'partyName': 'officer2', 'roles': ['Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of 1 Director',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_ATLEAST_THREE_DIRECTOR', 'CC',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Director']},
                {'partyName': 'officer2', 'roles': ['Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of 3 Director',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'SUCCESS', 'CP',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Director']},
                {'partyName': 'officer2', 'roles': ['Director']},
                {'partyName': 'officer3', 'roles': ['Director']}
            ],
            None, None
        ),
        (
            'FAIL_NO_COMPLETING_PARTY', 'CP',
            [
                {'partyName': 'officer1', 'roles': ['Director']},
                {'partyName': 'officer2', 'roles': ['Director']},
                {'partyName': 'officer3', 'roles': ['Director']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_INVALID_PARTY_ROLE', 'CP',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Director']},
                {'partyName': 'officer2', 'roles': ['Director']},
                {'partyName': 'officer3', 'roles': ['Director']},
                {'partyName': 'officer3', 'roles': ['Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Incorporator is an invalid party role',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_MINIMUM_3_DIRECTORS', 'CP',
            [
                {'partyName': 'officer1', 'roles': ['Completing Party', 'Director']},
                {'partyName': 'officer2', 'roles': ['Director']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of three Directors',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_NO_COMPLETING_PARTY', 'BC',
            [
                {'partyName': 'officer1', 'roles': ['Director', 'Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_NO_COMPLETING_PARTY', 'ULC',
            [
                {'partyName': 'officer1', 'roles': ['Director', 'Incorporator']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        ),
        (
            'FAIL_NO_COMPLETING_PARTY', 'CC',
            [
                {'partyName': 'officer1', 'roles': ['Director', 'Incorporator']},
                {'partyName': 'officer2', 'roles': ['Director']},
                {'partyName': 'officer3', 'roles': ['Director']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
        )
    ])
def test_validate_incorporation_role(session, minio_server, mocker, test_name,
                                     legal_type, parties, expected_code, expected_msg):
    """Assert that incorporation parties roles can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1}
    filing_json['filing']['business']['legalType'] = legal_type

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    if legal_type == 'CP':
        del filing_json['filing'][incorporation_application_name]['offices']['recordsOffice']
        del filing_json['filing'][incorporation_application_name]['parties'][1]
        del filing_json['filing'][incorporation_application_name]['shareStructure']
        del filing_json['filing'][incorporation_application_name]['incorporationAgreement']
        filing_json['filing'][incorporation_application_name]['cooperative'] = {
            'cooperativeAssociationType': 'CP'
        }

        # Provide mocked valid documents
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter, invalid=False)

    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['contactPoint']['email'] = 'no_one@never.get'
    filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = '123-456-7890'

    base_mailing_address = filing_json['filing'][incorporation_application_name]['parties'][0]['mailingAddress']
    base_delivery_address = filing_json['filing'][incorporation_application_name]['parties'][0]['deliveryAddress']
    filing_json['filing'][incorporation_application_name]['parties'] = []

    # populate party and party role info
    for index, party in enumerate(parties):
        mailing_addr = create_party_address(base_address=base_mailing_address)
        delivery_addr = create_party_address(base_address=base_delivery_address)
        p = create_party(party['roles'], index + 1, mailing_addr, delivery_addr)
        filing_json['filing'][incorporation_application_name]['parties'].append(p)

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, parties, expected_msg',
    [
        ('SUCCESS', 'CP',
         [
             {
                 'partyName': 'officer1', 'roles': ['Completing Party', 'Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             },
             {
                 'partyName': 'officer2', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer3', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'MB'}
             },
         ], None
         ),
        ('FAIL_ONE_IN_REGION_BC', 'CP',
         [
             {
                 'partyName': 'officer1', 'roles': ['Completing Party', 'Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer2', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer3', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdfd', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'MB'}
             },
         ], [{'error': 'Must have minimum of one BC mailing address',
              'path': '/filing/incorporationApplication/parties/mailingAddress'}]
         ),
        ('FAIL_MAJORITY_IN_COUNTRY_CA', 'CP',
         [
             {
                 'partyName': 'officer1', 'roles': ['Completing Party', 'Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'US',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer2', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'JP',
                                    'postalCode': 'h0h0h0', 'region': 'AICHI'}
             },
             {
                 'partyName': 'officer3', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             }
         ], [{'error': 'Must have majority of mailing addresses in Canada',
              'path': '/filing/incorporationApplication/parties/mailingAddress'}]
         ),
        ('FAIL_MAJORITY_IN_COUNTRY_CA_50_percent', 'CP',
         [
             {
                 'partyName': 'officer1', 'roles': ['Completing Party', 'Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'US',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer2', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'JP',
                                    'postalCode': 'h0h0h0', 'region': 'AICHI'}
             },
             {
                 'partyName': 'officer3', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             },
             {
                 'partyName': 'officer4', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             }
         ], [{'error': 'Must have majority of mailing addresses in Canada',
              'path': '/filing/incorporationApplication/parties/mailingAddress'}]
         ),
        ('PASS_MAJORITY_IN_COUNTRY_CA', 'CP',
         [
             {
                 'partyName': 'officer1', 'roles': ['Completing Party', 'Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'asdf', 'country': 'US',
                                    'postalCode': 'h0h0h0', 'region': 'AB'}
             },
             {
                 'partyName': 'officer2', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             },
             {
                 'partyName': 'officer3', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             },
             {
                 'partyName': 'officer4', 'roles': ['Director'],
                 'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                    'postalCode': 'h0h0h0', 'region': 'BC'}
             }
         ], None
         )
    ])
def test_validate_incorporation_parties_mailing_address(session, mocker, test_name, legal_type, parties, expected_msg):
    """Assert that incorporation parties mailing address is not empty."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1, 'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing']['business']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['contactPoint']['email'] = 'no_one@never.get'
    filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = '123-456-7890'
    filing_json['filing'][incorporation_application_name]['parties'] = []

    # populate party and party role info
    for index, party in enumerate(parties):

        party_ma = party['mailingAddress']
        mailing_addr = create_party_address(street=party_ma['street'],
                                            street_additional='street additional',
                                            city=party_ma['city'],
                                            country=party_ma['country'],
                                            postal_code=party_ma['postalCode'],
                                            region=party_ma['region'])
        p = create_party(party['roles'], index + 1, mailing_addr, None)
        filing_json['filing'][incorporation_application_name]['parties'].append(p)

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate_coop_parties_mailing_address(filing_json)

    # validate outcomes
    if expected_msg:
        assert lists_are_equal(err, expected_msg)
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, legal_type, parties, expected_msg',
    [
        (
            'SUCCESS_VALID_FIRST_MIDDLE_LAST_NAME_LENGTHS', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfja', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': '', 'lastName': 'Doe'}
                },
                                {
                    'partyName': 'officer3',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': '  ', 'lastName': 'Doe'}
                }
            ],
            None
        ),
        (
            'FAIL_FIRST_NAME_EMPTY', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': '', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': '', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator first name is required',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director first name is required',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_LAST_NAME_EMPTY', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Johnajksdfjldkslfja', 'middleName': None, 'lastName': ''}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': 'jkalsdf', 'lastName': ''}
                }
            ],
            [{'error': 'Completing Party, Incorporator last name is required',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director last name is required',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_FIRST_NAME_LEADING_AND_TRAILING_WHITESPACE', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': '  John', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'John  ', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator first name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director first name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_MIDDLE_NAME_LEADING_AND_TRAILING_WHITESPACE', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'John', 'middleName': '  B', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'John', 'middleName': 'B  ', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator middle name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director middle name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_LAST_NAME_LEADING_AND_TRAILING_WHITESPACE', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Johnajksdfjldkslfja', 'middleName': None, 'lastName': '  Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': 'jkalsdf', 'lastName': 'Doe  '}
                }
            ],
            [{'error': 'Completing Party, Incorporator last name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director last name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_FIRST_MIDDLE_LAST_NAME_WHITESPACE', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': ' John  ', 'middleName': ' B ', 'lastName': '  Doe  '}
                },
            ],
            [{'error': 'Completing Party, Incorporator first name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Incorporator middle name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Incorporator last name cannot start or end with whitespace',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_FIRST_NAME_WHITESPACE_ONLY', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': '  ', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': '  ', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator first name is required',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director first name is required',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_LAST_NAME_WHITESPACE_ONLY', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfja', 'middleName': None, 'lastName': '  '}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': 'jkalsdf', 'lastName': '  '}
                }
            ],
            [{'error': 'Completing Party, Incorporator last name is required',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director last name is required',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_FIRST_LAST_NAME_WHITESPACE_ONLY', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': '   ', 'middleName': '   ', 'lastName': '   '}
                },
            ],
            [{'error': 'Completing Party, Incorporator first is required',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Incorporator last name is required',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_FIRST_NAME_TOO_LONG', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfjab', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Incorporator', 'Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfjab', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Incorporator, Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_MIDDLE_NAME_TOO_LONG', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'John', 'middleName': 'Johnajksdfjljdkslfjab', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane', 'middleName': 'Johnajksdfjljdkslfjab', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Incorporator middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_LAST_NAME_TOO_LONG', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'John', 'middleName': 'None', 'lastName': 'Doeasdfasdfasdfasdfasdfasdfasdf'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane', 'middleName': 'jkalsdf', 'lastName': 'Doeasdfasdfasdfasdfasdfasdfasdf'}
                }
            ],
            [{'error': 'Completing Party, Incorporator last name cannot be longer than 30 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director last name cannot be longer than 30 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_FIRST_AND_MIDDLE_NAME_AND_LAST_NAME_TOO_LONG', 'BEN',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Incorporator'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfjab',
                                'middleName': 'Janeajksdfjljdkslfjab',
                                'lastName': 'Doeasdfasdfasdfasdfasdfasdfasdf'}
                },
            ],
            [{'error': 'Completing Party, Incorporator first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Incorporator middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Incorporator last name cannot be longer than 30 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'SUCCESS_VALID_FIRST_MIDDLE_NAME_LENGTHS', 'CP',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Director'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfja', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer3',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane', 'middleName': None, 'lastName': 'Doe'}
                }
            ],
            None
        ),
        (
            'FAIL_PARTY_FIRST_NAME_TOO_LONG', 'CP',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Director'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfjab', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane1jksdfjljdkslfjab', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer3',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane2jksdfjljdkslfjab', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_MIDDLE_NAME_TOO_LONG', 'CP',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Director'],
                    'officer': {'firstName': 'John', 'middleName': 'Johnajksdfjljdkslfjab', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane1', 'middleName': None, 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer3',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane2', 'middleName': 'Jane2ajksdfjljdkslfjab', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'}]
        ),
        (
            'FAIL_PARTY_FIRST_AND_MIDDLE_NAME_TOO_LONG', 'CP',
            [
                {
                    'partyName': 'officer1',
                    'roles': ['Completing Party', 'Director'],
                    'officer': {'firstName': 'Johnajksdfjljdkslfjab', 'middleName': 'Johnajksdfjljdkslfjab', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer2',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane1jksdfjljdkslfjab', 'middleName': 'Jane1ajksdfjljdkslfjab', 'lastName': 'Doe'}
                },
                {
                    'partyName': 'officer3',
                    'roles': ['Director'],
                    'officer': {'firstName': 'Jane2jksdfjljdkslfjab', 'middleName': 'Jane2ajksdfjljdkslfjab', 'lastName': 'Doe'}
                }
            ],
            [{'error': 'Completing Party, Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director first name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Completing Party, Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'},
             {'error': 'Director middle name cannot be longer than 20 characters',
              'path': '/filing/incorporationApplication/parties'}]
        )
    ])
def test_validate_incorporation_party_names(session, mocker, test_name,
                                            legal_type, parties, expected_msg):
    """Assert that incorporation parties roles can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1, 'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    base_officer = filing_json['filing'][incorporation_application_name]['parties'][0]['officer']
    filing_json['filing']['business']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name]['contactPoint']['email'] = 'no_one@never.get'
    filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = '123-456-7890'
    filing_json['filing'][incorporation_application_name]['parties'] = []

    # populate party and party role info
    for index, party in enumerate(parties):
        officer = party['officer']
        first_name = officer['firstName']
        middle_name = officer['middleName']
        last_name = officer['lastName']

        base_officer_copy = copy.deepcopy(base_officer)
        officer = create_officer(base_officer=base_officer_copy,
                                 first_name=first_name,
                                 middle_name=middle_name,
                                 last_name=last_name)
        p = create_party(roles=party['roles'], officer=officer)
        filing_json['filing'][incorporation_application_name]['parties'].append(p)

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate_parties_names(filing_json, incorporation_application_name, legal_type)

    # validate outcomes
    if expected_msg:
        assert lists_are_equal(err, expected_msg)
    else:
        assert not err


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
             'path': '/filing/incorporationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BEN',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_EMPTY_CLASS_NAME', 'BEN', '', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class name is required.',
             'path': '/filing/incorporationApplication/shareClasses/0/name/'
         }]),
        ('FAIL_WHITESPACE_ONLY_CLASS_NAME', 'BEN', '   ', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class name is required.',
             'path': '/filing/incorporationApplication/shareClasses/0/name/'
         }]),
        ('FAIL_LEADING_AND_TRAILING_WHITESPACE_CLASS_NAME', 'BEN', ' Share Series 1 ', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class name cannot start or end with whitespace.',
             'path': '/filing/incorporationApplication/shareClasses/0/name/'
         }]),
        ('FAIL_EMPTY_SERIES_NAME', 'BEN', 'Share Class 1', True, 5000, True, 0.875, 'CAD', '', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series name is required.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/name/'
         }]),
        ('FAIL_WHITESPACE_ONLY_SERIES_NAME', 'BEN', 'Share Class 1', True, 5000, True, 0.875, 'CAD', '   ', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series name is required.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/name/'
         }]),
        ('FAIL_LEADING_AND_TRAILING_WHITESPACE_SERIES_NAME', 'BEN', 'Share Class 1', True, 5000, True, 0.875, 'CAD', '  Share Series 1  ', True, 1000,
         None, None,  HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series name cannot start or end with whitespace.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/name/'
         }]), 
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BEN',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/incorporationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BEN',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/incorporationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BEN',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
            HTTPStatus.BAD_REQUEST, [{
                'error':
                'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
                'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
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
             'path': '/filing/incorporationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'BC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'BC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'BC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/incorporationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'BC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/incorporationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'BC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'BC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
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
             'path': '/filing/incorporationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'ULC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'ULC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/incorporationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'ULC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/incorporationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'ULC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
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
             'path': '/filing/incorporationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2', 'CC',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES', 'CC',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY', 'CC',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/incorporationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE', 'CC',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/incorporationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES', 'CC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES', 'CC',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error':
             'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }])
    ])
def test_validate_incorporation_share_classes(session, mocker, test_name, legal_type,
                                              class_name_1, class_has_max_shares, class_max_shares,
                                              has_par_value, par_value, currency, series_name_1, series_has_max_shares,
                                              series_max_shares,
                                              class_name_2, series_name_2,
                                              expected_code, expected_msg):
    """Assert that validator validates share class correctly."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1, 'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = 'NR 1234567'
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    filing_json['filing']['business']['legalType'] = legal_type

    base_mailing_address = filing_json['filing'][incorporation_application_name]['parties'][0]['mailingAddress']
    base_delivery_address = filing_json['filing'][incorporation_application_name]['parties'][0]['deliveryAddress']
    filing_json['filing'][incorporation_application_name]['parties'] = []

    parties = [
        {'partyName': 'officer1', 'roles': ['Director', 'Completing Party']},
        {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']},
        {'partyName': 'officer3', 'roles': ['Director']}
    ]

    # populate party and party role info
    for index, party in enumerate(parties):
        mailing_addr = create_party_address(base_address=base_mailing_address)
        delivery_addr = create_party_address(base_address=base_delivery_address)
        p = create_party(party['roles'], index + 1, mailing_addr, delivery_addr)
        filing_json['filing'][incorporation_application_name]['parties'].append(p)

    share_structure = filing_json['filing'][incorporation_application_name]['shareStructure']

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

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


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
    ])
@not_github_ci
def test_validate_incorporation_effective_date(session, mocker, test_name, effective_date, expected_code, expected_msg):
    """Assert that validator validates effective date correctly."""
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'].pop('business')
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1}

    if effective_date is not None:
        filing_json['filing']['header']['effectiveDate'] = effective_date

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        if err:
            print(err, err.code, err.msg)
        assert err is None


rules_file_key_path = '/filing/incorporationApplication/cooperative/rulesFileKey'
memorandum_file_key_path = '/filing/incorporationApplication/cooperative/memorandumFileKey'


@pytest.mark.parametrize(
    'test_name, key, scenario, expected_code, expected_msg',
    [
        ('SUCCESS', 'rulesFileKey', 'success', None, None),
        ('SUCCESS', 'memorandumFileKey', 'success', None, None),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'failRules',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.', 'path': rules_file_key_path
            }]),
        ('FAIL_INVALID_MEMORANDUM_FILE_KEY', 'memorandumFileKey', 'failMemorandum',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.', 'path': memorandum_file_key_path
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidRulesSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
                'path': rules_file_key_path
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidMemorandumSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.',
                'path': memorandum_file_key_path
            }]),
    ])
def test_validate_cooperative_documents(session, mocker, minio_server, test_name, key, scenario, expected_code,
                                        expected_msg):
    """Assert that validator validates cooperative documents correctly."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                                       'email': 'no_one@never.get', 'filingId': 1}
    legal_type = 'CP'
    filing_json['filing']['business']['legalType'] = legal_type
    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = legal_type
    del filing_json['filing'][incorporation_application_name]['offices']['recordsOffice']
    del filing_json['filing'][incorporation_application_name]['parties'][1]
    del filing_json['filing'][incorporation_application_name]['shareStructure']
    del filing_json['filing'][incorporation_application_name]['incorporationAgreement']
    filing_json['filing'][incorporation_application_name]['cooperative'] = {
        'cooperativeAssociationType': 'CP'
    }

    # Add minimum director requirements
    director = filing_json['filing'][incorporation_application_name]['parties'][0]['roles'][1]
    filing_json['filing'][incorporation_application_name]['parties'][0]['roles'].append(director)
    filing_json['filing'][incorporation_application_name]['parties'][0]['roles'].append(director)

    # Mock upload file for test scenarios
    if scenario == 'success':
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'failRules':
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = scenario
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'failMemorandum':
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = scenario
    if scenario == 'invalidRulesSize':
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter, invalid=True)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter, invalid=False)
    if scenario == 'invalidMemorandumSize':
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter, invalid=False)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter, invalid=True)

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_name_request',
                 return_value=[])

    # perform test
    err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name', [
        ('with_court_order'),
        ('without_court_order')
    ])
def test_ia_court_order(session, mocker, test_name):
    """Assert that incorporation court order can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1,
                                       'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    if test_name == 'with_court_order':
        filing_json['filing'][incorporation_application_name]['courtOrder'] = COURT_ORDER
        filing_json['filing'][incorporation_application_name]['courtOrder']['orderDate'] = court_order_date

    mocker.patch('legal_api.services.filings.validations.incorporation_application.validate_roles',
                 return_value=[])

    # perform test
    with freeze_time(now):
        err = validate(None, filing_json)

    assert err is None


@pytest.mark.parametrize(
    'legal_type, has_rights_or_restrictions, has_series, should_pass',
    [
        (Business.LegalTypes.BCOMP.value, False, True, False),
        (Business.LegalTypes.BCOMP.value, False, False, True),
        (Business.LegalTypes.BCOMP.value, True, True, True),
        (Business.LegalTypes.BCOMP.value, True, False, True),

        (Business.LegalTypes.BC_ULC_COMPANY.value, False, True, False),
        (Business.LegalTypes.BC_ULC_COMPANY.value, False, False, True),
        (Business.LegalTypes.BC_ULC_COMPANY.value, True, True, True),
        (Business.LegalTypes.BC_ULC_COMPANY.value, True, False, True),

        (Business.LegalTypes.BC_CCC.value, False, True, False),
        (Business.LegalTypes.BC_CCC.value, False, False, True),
        (Business.LegalTypes.BC_CCC.value, True, True, True),
        (Business.LegalTypes.BC_CCC.value, True, False, True),

        (Business.LegalTypes.COMP.value, False, True, False),
        (Business.LegalTypes.COMP.value, False, False, True),
        (Business.LegalTypes.COMP.value, True, True, True),
        (Business.LegalTypes.COMP.value, True, False, True),
    ]
)
def test_incorporation_application_share_class_series_validation(mocker, app, session, legal_type,
                                                       has_rights_or_restrictions, has_series, should_pass):
    """Test share class/series validation in incorporation application."""
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'].pop('business')
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)

    if 'shareStructure' in filing_json['filing'][incorporation_application_name]:
        for share_class in filing_json['filing'][incorporation_application_name]['shareStructure']['shareClasses']:
            share_class['hasRightsOrRestrictions'] = has_rights_or_restrictions
            if not has_rights_or_restrictions:
                if not has_series:
                    share_class.pop('series', None)

    err = validate(None, filing_json)

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
def test_validate_incorporation_application_parties_delivery_address(mocker, app, session, test_name,
                                                                     has_delivery_address, expected_code, expected_msg):
    """Test parties delivery address validation in incorporation application."""
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'].pop('business')
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)

    if not has_delivery_address:
        if 'deliveryAddress' in filing_json['filing'][incorporation_application_name]['parties'][0]:
            del filing_json['filing'][incorporation_application_name]['parties'][0]['deliveryAddress']

    err = validate(None, filing_json)

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
def test_ia_phone_number_validation(session, should_pass, phone_number, extension):
    """Test validate phone number and / or extension if they are provided."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1,
                                       'effectiveDate': effective_date}

    if phone_number:
        filing_json['filing'][incorporation_application_name]['contactPoint']['phone'] = phone_number
    if extension:
        filing_json['filing'][incorporation_application_name]['contactPoint']['extension'] = extension

    # perform test
    with freeze_time(now):
        err = validate(None, filing_json)

    if should_pass:
        assert None is err
    else:
        assert err
        assert HTTPStatus.BAD_REQUEST == err.code

@pytest.mark.parametrize('test_name, name_translation, expected_code, expected_msg', [
    ('SUCCESS_EMPTY_ARRAY', [], None, None),
    ('SUCCESS_NAME_TRANSLATION', [{"name": "TEST"}], None, None),
    ('FAIL_EMPTY_NAME_TRANSLATION', [{"name": ""}],  HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/incorporationApplication/nameTranslations/0/name/'
    }]),
    ('FAIL_WHITESPACE_ONLY_NAME_TRANSLATION', [{"name": "   "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/incorporationApplication/nameTranslations/0/name/'
    }]),
    ('FAIL_SECOND_NAME_TRANSLATION', [{"name": "TEST"}, {"name": "   "}], HTTPStatus.BAD_REQUEST, [{
        'error': 'Name translation cannot be an empty string.',
        'path': '/filing/incorporationApplication/nameTranslations/1/name/'
    }]),
])
def test_validate_name_translation(session, test_name, name_translation, expected_code, expected_msg):
    """Test validate name translation if provided."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08',
                                       'certifiedBy': 'full name', 'email': 'no_one@never.get', 'filingId': 1,
                                       'effectiveDate': effective_date}
    
    filing_json['filing'][incorporation_application_name]['nameTranslations'] = name_translation

    # perform test
    with freeze_time(now):
        err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        if err:
            print(err, err.code, err.msg)
        assert err is None
