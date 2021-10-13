# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests to assure the business-filing end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import copy
import datetime
from http import HTTPStatus
import requests
from unittest.mock import patch
import pytest

from registry_schemas.example_data import ALTERATION_FILING_TEMPLATE
from flask_jwt_oidc import JwtManager

from legal_api.models import Business, Filing
from legal_api.services.authz import STAFF_ROLE
from tests import integration_namerequests, integration_payment
from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing
from tests.unit.services.utils import create_header
from legal_api.resources.v1.business.business_filings import ListFilingResource
from unittest import mock

@integration_payment
@integration_namerequests
def test_alteration_success_bc_to_ben(client, jwt, session):
    """Assert that a valid BC to BEN alteration can be posted."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = Business.LegalTypes.COMP.value
    filing['filing']['alteration']['business']['legalType'] = Business.LegalTypes.BCOMP.value

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'alteration'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


@integration_payment
@integration_namerequests
def test_alteration_success_ben_to_bc(client, jwt, session):
    """Assert that a valid BEN to BC alteration can be posted."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)

    filing = copy.deepcopy(ALTERATION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = Business.LegalTypes.BCOMP.value
    filing['filing']['alteration']['business']['legalType'] = Business.LegalTypes.COMP.value

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['name'] == 'alteration'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def mocked_requests_post(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return MockResponse({'type': 'PAYMENT_ERROR',
                         'detail': 'Unable to create payment!!!'}, 400)



@pytest.mark.parametrize('test_name, staff_payment', [
    ('Staff payment', True),
    ('External user payment', False)
])
def test_create_invoice_fail(session, jwt, test_name, staff_payment):
    """Assert that a message is built given pay-api response."""
    identifier = 'BC1156638'
    b = factory_business(identifier, datetime.datetime.utcnow(), None, Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)
    filing_json = {
                    'filing': {
                        'header': {
                            'name': 'alteration',
                            'certifiedBy': 'John McCaully',
                            'date': '2021-10-12',
                            'folioNumber': '',
                            'routingSlipNumber': '222222222',
                            'priority': False
                        },
                        'business': {
                            'foundingDate': '2021-10-04T20:54:52.970528+00:00',
                            'legalType': 'BEN',
                            'identifier': identifier,
                            'legalName': '1156638 B.C. LTD.'
                        },
                        'alteration': {
                            'business': {
                                'identifier': identifier,
                                'legalType': 'BEN'
                            },
                            'provisionsRemoved': False,
                            'contactPoint': {
                                'email': 'andre.pestana@aot-technologies.com',
                                'phone': '(123) 456-7890'
                            },
                            'nameTranslations': [
                                {
                                    'name': 'Traducción'
                                }
                            ]
                        }
                    }
                }
    filing = factory_filing(b, filing_json)
    filing_types = [{'filingTypeCode': 'ALTER', 'priority': False, 'waiveFees': False}]

    with patch.object(requests, 'post', return_value=mocked_requests_post()), \
         patch.object(JwtManager, 'get_token_auth_header', return_value='1234567890'), \
         patch.object(JwtManager, 'validate_roles', return_value = True if staff_payment else False):
        response = ListFilingResource._create_invoice(b,
                                                      filing,
                                                      filing_types,
                                                      jwt,
                                                      None)

    assert response
    assert response[0]['payment_error_type'] == 'PAYMENT_ERROR'
    assert response[0]['message'] == 'Unable to create payment!!!'
    assert response[1] == 402

    if staff_payment:
        assert Filing.find_by_id(filing.id) == None
    else:
        updated_filing = Filing.find_by_id(filing.id)
        assert updated_filing
        assert updated_filing.payment_status_code == 'PAYMENT_ERROR'
