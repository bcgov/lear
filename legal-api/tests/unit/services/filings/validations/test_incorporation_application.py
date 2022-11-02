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
import io
from datetime import date
from http import HTTPStatus

import datedelta
import pytest
from registry_schemas.example_data.schema_data import FILING_HEADER
import requests
from freezegun import freeze_time
from reportlab.lib.pagesizes import legal, letter
from reportlab.pdfgen import canvas
from registry_schemas.example_data import COOP_INCORPORATION, INCORPORATION, INCORPORATION_FILING_TEMPLATE

from legal_api.models import Business
from legal_api.services import MinioService
from legal_api.services.filings import validate
from legal_api.services.filings.validations.incorporation_application import validate_parties_mailing_address, validate_parties_names

from . import create_party, create_party_address, lists_are_equal, create_officer
from tests import not_github_ci


# setup
identifier = 'NR 1234567'
now = date(2020, 9, 17)
founding_date = now - datedelta.YEAR
business = Business(identifier=identifier)
effective_date = '2020-09-18T00:00:00+00:00'
incorporation_application_name = 'incorporationApplication'


@pytest.mark.parametrize(
    'test_name, delivery_region, delivery_country, mailing_region, mailing_country, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', 'CA', 'BC', 'CA', None, None),
        ('FAIL_NOT_BC_DELIVERY_REGION', 'AB', 'CA', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                    'path':
                    '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressRegion'}
            ]),
        ('FAIL_NOT_BC_MAILING_REGION', 'BC', 'CA', 'AB', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressRegion'},
                {'error': "Address Region must be 'BC'.",
                 'path':
                 '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressRegion'}
            ]),
        ('FAIL_ALL_ADDRESS_REGIONS', 'WA', 'CA', 'WA', 'CA',
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
        ('FAIL_NOT_DELIVERY_COUNTRY', 'BC', 'NZ', 'BC', 'CA',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/deliveryAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/deliveryAddress/addressCountry'}
            ]),
        ('FAIL_NOT_MAILING_COUNTRY', 'BC', 'CA', 'BC', 'NZ',
            HTTPStatus.BAD_REQUEST, [
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/registeredOffice/mailingAddress/addressCountry'},
                {'error': "Address Country must be 'CA'.",
                 'path': '/filing/incorporationApplication/offices/recordsOffice/mailingAddress/addressCountry'}
            ]),
        ('FAIL_ALL_ADDRESS', 'AB', 'NZ', 'AB', 'NZ',
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
def test_validate_incorporation_addresses_basic(session, test_name, delivery_region, delivery_country, mailing_region,
                                                mailing_country, expected_code, expected_msg):
    """Assert that incorporation offices can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                             'email': 'no_one@never.get', 'filingId': 1, 'effectiveDate': effective_date}

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)
    filing_json['filing'][incorporation_application_name]['nameRequest'] = {}
    filing_json['filing'][incorporation_application_name]['nameRequest']['nrNumber'] = identifier
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = Business.LegalTypes.BCOMP.value
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
            'FAIL_NO_COMPLETING_PARTY', 'BEN',
            [
                {'partyName': 'officer1', 'roles': ['Director', 'Incorporator']},
                {'partyName': 'officer2', 'roles': ['Incorporator', 'Director']}
            ],
            HTTPStatus.BAD_REQUEST, [{'error': 'Must have a minimum of one completing party',
                                      'path': '/filing/incorporationApplication/parties/roles'}]
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
        )
    ])
def test_validate_incorporation_role(session, minio_server, test_name,
                                     legal_type, parties, expected_code, expected_msg):
    """Assert that incorporation parties roles can be validated."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                             'email': 'no_one@never.get', 'filingId': 1}
    filing_json['filing']['business']['legalType'] = legal_type

    if legal_type == 'CP':
        filing_json['filing'][incorporation_application_name] = copy.deepcopy(COOP_INCORPORATION)
        # Provide mocked valid documents
        filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter)
        filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter)
    else:
        filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)

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
        ('SUCCESS', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': '123 st', 'city': 'Vancouver', 'country': 'CA',
                                 'postalCode': 'h0h0h0', 'region': 'BC'}}
         ], None
         ),
        ('FAIL_INVALID_STREET', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': None, 'city': 'Vancouver', 'country': 'CA',
                                 'postalCode': 'h0h0h0', 'region': 'BC'}},
         ], [{'error': 'Person 1: Mailing address streetAddress None is invalid',
              'path': '/filing/incorporationApplication/parties/1/mailingAddress/streetAddress/None/'}]
         ),
        ('FAIL_INVALID_CITY', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': '123 St', 'city': None, 'country': 'CA',
                                 'postalCode': 'h0h0h0', 'region': 'BC'}},
         ], [{'error': 'Person 1: Mailing address addressCity None is invalid',
              'path': '/filing/incorporationApplication/parties/1/mailingAddress/addressCity/None/'}]
         ),
        ('FAIL_INVALID_COUNTRY', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': '123 St', 'city': 'Vancouver', 'country': None,
                                 'postalCode': 'h0h0h0', 'region': 'BC'}},
         ], [{'error': 'Person 1: Mailing address addressCountry None is invalid',
              'path': '/filing/incorporationApplication/parties/1/mailingAddress/addressCountry/None/'}]
         ),
        ('FAIL_INVALID_POSTAL_CODE', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': '123 St', 'city': 'Vancouver', 'country': 'CA',
                                 'postalCode': None, 'region': 'BC'}},
         ], [{'error': 'Person 1: Mailing address postalCode None is invalid',
              'path': '/filing/incorporationApplication/parties/1/mailingAddress/postalCode/None/'}]
         ),
        ('FAIL_INVALID_REGION', 'BEN',
         [
             {'partyName': 'officer1', 'roles': ['Director'],
              'mailingAddress': {'street': '123 St', 'city': 'Vancouver', 'country': 'CA',
                                 'postalCode': 'h0h0h0', 'region': None}},
         ], [{'error': 'Person 1: Mailing address addressRegion None is invalid',
              'path': '/filing/incorporationApplication/parties/1/mailingAddress/addressRegion/None/'}]
         ),
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
         ),
    ])
def test_validate_incorporation_parties_mailing_address(session, test_name, legal_type, parties, expected_msg):
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

    # perform test
    with freeze_time(now):
        err = validate_parties_mailing_address(filing_json)

    # validate outcomes
    if expected_msg:
        assert lists_are_equal(err, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, legal_type, parties, expected_msg',
    [
        (
                'SUCCESS_VALID_FIRST_MIDDLE_NAME_LENGTHS', 'BEN',
                [
                    {
                        'partyName': 'officer1',
                        'roles': ['Completing Party', 'Incorporator'],
                        'officer': {'firstName': 'Johnajksdfjljdkslfja', 'middleName': None, 'lastName': 'Doe'}
                    },
                    {
                        'partyName': 'officer2',
                        'roles': ['Incorporator', 'Director'],
                        'officer': {'firstName': 'Janeajksdfjljdkslfja', 'middleName': 'jkalsdf', 'lastName': 'Doe'}
                    }
                ],
                None
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
                'FAIL_PARTY_FIRST_AND_MIDDLE_NAME_TOO_LONG', 'BEN',
                [
                    {
                        'partyName': 'officer1',
                        'roles': ['Completing Party', 'Incorporator'],
                        'officer': {'firstName': 'Janeajksdfjljdkslfjab', 'middleName': 'Janeajksdfjljdkslfjab', 'lastName': 'Doe'}
                    },
                ],
                [{'error': 'Completing Party, Incorporator first name cannot be longer than 20 characters',
                  'path': '/filing/incorporationApplication/parties'},
                 {'error': 'Completing Party, Incorporator middle name cannot be longer than 20 characters',
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
def test_validate_incorporation_party_names(session, test_name,
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

    # perform test
    with freeze_time(now):
        err = validate_parties_names(filing_json)

    # validate outcomes
    if expected_msg:
        assert lists_are_equal(err, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, '
    'class_name_1,class_has_max_shares,class_max_shares,has_par_value,par_value,currency,'
    'series_name_1,series_has_max_shares,series_max_shares,'
    'class_name_2,series_name_2,'
    'expected_code, expected_msg',
    [
        ('SUCCESS', 'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'Share Class 1', False, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None, None, None),
        ('SUCCESS', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         None, None, None, None),
        ('SUCCESS-CLASS2', 'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', None, None, None),
        ('FAIL-CLASS2',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 1', None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/1/name/'
         }]),
        ('FAIL-SERIES2',
         'Share Class 1', False, None, False, None, None, 'Share Series 1', False, None,
         'Share Class 2', 'Share Series 1',
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 name already used in a share class or series.',
             'path': '/filing/incorporationApplication/shareClasses/0/series/1'
         }]),
        ('FAIL_INVALID_CLASS_MAX_SHARES',
         'Share Class 1', True, None, True, 0.875, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/maxNumberOfShares/'
         }]),
        ('FAIL_INVALID_CURRENCY',
         'Share Class 1', True, 5000, True, 0.875, None, 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify currency',
             'path': '/filing/incorporationApplication/shareClasses/0/currency/'
         }]),
        ('FAIL_INVALID_PAR_VALUE',
         'Share Class 1', True, 5000, True, None, 'CAD', 'Share Series 1', True, 1000,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share class Share Class 1 must specify par value',
             'path': '/filing/incorporationApplication/shareClasses/0/parValue/'
         }]),
        ('FAIL_INVALID_SERIES_MAX_SHARES',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, None,
         None, None,
         HTTPStatus.BAD_REQUEST, [{
             'error': 'Share series Share Series 1 must provide value for maximum number of shares',
             'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
         }]),
        ('FAIL_SERIES_SHARES_EXCEEDS_CLASS_SHARES',
         'Share Class 1', True, 5000, True, 0.875, 'CAD', 'Share Series 1', True, 10000,
         None, None,
            HTTPStatus.BAD_REQUEST, [{
                'error':
                'Series Share Series 1 share quantity must be less than or equal to that of its class Share Class 1',
                'path': '/filing/incorporationApplication/shareClasses/0/series/0/maxNumberOfShares'
            }])
    ])
def test_validate_incorporation_share_classes(session, test_name,
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
    filing_json['filing'][incorporation_application_name]['nameRequest']['legalType'] = 'BC'
    filing_json['filing']['business']['legalType'] = 'BEN'

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
                'error': '2020-09-18T00:00:00Z is an invalid ISO format for effective_date.'
            }]),
        ('FAIL_INVALID_DATE_TIME_MINIMUM', '2020-09-17T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a minimum of 2 minutes ahead.'
            }]),
        ('FAIL_INVALID_DATE_TIME_MAXIMUM', '2020-09-27T00:01:00+00:00',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid Datetime, effective date must be a maximum of 10 days ahead.'
            }])
    ])
@not_github_ci
def test_validate_incorporation_effective_date(session, test_name, effective_date, expected_code, expected_msg):
    """Assert that validator validates share class correctly."""
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'].pop('business')
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                             'email': 'no_one@never.get', 'filingId': 1}

    if effective_date is not None:
        filing_json['filing']['header']['effectiveDate'] = effective_date

    filing_json['filing'][incorporation_application_name] = copy.deepcopy(INCORPORATION)

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


@pytest.mark.parametrize(
    'test_name, key, scenario, expected_code, expected_msg',
    [
        ('SUCCESS', 'rulesFileKey', 'success', None, None),
        ('SUCCESS', 'memorandumFileKey', 'success', None, None),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'failRules',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.'
            }]),
        ('FAIL_INVALID_MEMORANDUM_FILE_KEY', 'memorandumFileKey', 'failMemorandum',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Invalid file.'
            }]),
        ('FAIL_INVALID_RULES_KEY', 'rulesFileKey', '',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'A valid rules key is required.'
            }]),
        ('FAIL_INVALID_RULES_NAME', 'rulesFileName', '',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'A valid rules file name is required.'
            }]),
        ('FAIL_INVALID_MEMORANDUM_KEY', 'memorandumFileKey', '',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'A valid memorandum key is required.'
            }]),
        ('FAIL_INVALID_MEMORANDUM_NAME', 'memorandumFileName', '',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'A valid memorandum file name is required.'
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidRulesSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.'
            }]),
        ('FAIL_INVALID_RULES_FILE_KEY', 'rulesFileKey', 'invalidMemorandumSize',
            HTTPStatus.BAD_REQUEST, [{
                'error': 'Document must be set to fit onto 8.5” x 11” letter-size paper.'
            }]),
    ])
def test_validate_cooperative_documents(session, minio_server, test_name, key, scenario, expected_code, expected_msg):
    """Assert that validator validates cooperative documents correctly."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['header'] = {'name': incorporation_application_name, 'date': '2019-04-08', 'certifiedBy': 'full name',
                             'email': 'no_one@never.get', 'filingId': 1}
    filing_json['filing']['business']['legalType'] = 'CP'
    filing_json['filing'][incorporation_application_name] = copy.deepcopy(COOP_INCORPORATION)

    # Add minimum director requirements
    director = filing_json['filing'][incorporation_application_name]['parties'][0]['roles'][1]
    filing_json['filing'][incorporation_application_name]['parties'][0]['roles'].append(director)
    filing_json['filing'][incorporation_application_name]['parties'][0]['roles'].append(director)

    # Mock upload file for test scenarios
    if scenario:
        if scenario == 'success':
            filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter)
            filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter)
        if scenario == 'failRules':
            filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = scenario
            filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter)
        if scenario == 'failMemorandum':
            filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter)
            filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = scenario
        if scenario == 'invalidRulesSize':
            filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(legal)
            filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(letter)
        if scenario == 'invalidMemorandumSize':
            filing_json['filing'][incorporation_application_name]['cooperative']['rulesFileKey'] = _upload_file(letter)
            filing_json['filing'][incorporation_application_name]['cooperative']['memorandumFileKey'] = _upload_file(legal)
    else:
        # Assign key and value to test empty variables for failures
        key_value = ''
        filing_json['filing'][incorporation_application_name]['cooperative'][key] = key_value

    # perform test
    err = validate(business, filing_json)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


def _upload_file(page_size):
    signed_url = MinioService.create_signed_put_url('cooperative-test.pdf')
    key = signed_url.get('key')
    pre_signed_put = signed_url.get('preSignedUrl')

    requests.put(pre_signed_put, data=_create_pdf_file(page_size).read(),
                 headers={'Content-Type': 'application/octet-stream'})
    return key


def _create_pdf_file(page_size):
    buffer = io.BytesIO()
    can = canvas.Canvas(buffer, pagesize=page_size)
    doc_height = letter[1]

    for _ in range(3):
        text = 'This is a test document.\nThis is a test document.\nThis is a test document.'
        text_x_margin = 100
        text_y_margin = doc_height - 300
        line_height = 14
        _write_text(can, text, line_height, text_x_margin, text_y_margin)
        can.showPage()

    can.save()
    buffer.seek(0)
    return buffer


def _write_text(can, text, line_height, x_margin, y_margin):
    """Write text lines into a canvas."""
    for line in text.splitlines():
        can.drawString(x_margin, y_margin, line)
        y_margin -= line_height
