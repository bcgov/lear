# Copyright © 2021 Province of British Columbia
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

"""Tests to assure the business-filing end-point - LEDGER SEARCH

Test-Suite to ensure that the /businesses/_id_/filings LEDGER SEARCH endpoint is working as expected.
"""
import copy
import json
import re
from datetime import date, datetime
from http import HTTPStatus
from typing import Final, Tuple

import datedelta
import pytest
from dateutil.parser import parse
from flask import current_app
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CORRECTION_AR,
    CORRECTION_INCORPORATION,
    COURT_ORDER,
    FILING_HEADER,
    FILING_TEMPLATE,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)
from registry_schemas.example_data.schema_data import INCORPORATION

from legal_api.core import Filing, FilingMeta, FILINGS
from legal_api.models import Business, Comment, Filing as FilingStorage, UserRoles
from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import api_v2, integration_payment
from tests.unit.core.test_filing_ledger import load_ledger
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
    factory_user,
)
from tests.unit.services.utils import create_header, helper_create_jwt


def basic_test_helper():
    identifier = 'CP7654321'
    business = factory_business(identifier)

    filing_json = FILING_HEADER
    filing_json['specialResolution'] = SPECIAL_RESOLUTION
    filing_date = datetime.utcnow()
    filing = factory_completed_filing(business, filing_json, filing_date=filing_date)

    return business, filing


def test_not_authorized(session, client, jwt):
    """Assert the the call fails for unauthorized access."""
    business, filing = basic_test_helper()

    MISSING_ROLES = ['SOME RANDO ROLE',]

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, MISSING_ROLES, business.identifier))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED
    assert rv.json.get('message')
    assert business.identifier in rv.json.get('message')


def test_missing_business(session, client, jwt):
    """Assert the the call fails for missing business."""
    business, filing = basic_test_helper()

    not_the_business_identifier = 'ABC123'

    rv = client.get(f'/api/v2/businesses/{not_the_business_identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE,], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json.get('message')
    assert not_the_business_identifier in rv.json.get('message')


def test_missing_filing(session, client, jwt):
    """Assert the the call fails for missing business."""
    business, filing = basic_test_helper()

    wrong_filing_number = 999999999

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{wrong_filing_number}/documents',
                    headers=create_header(jwt, [STAFF_ROLE,], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json.get('message')
    assert str(wrong_filing_number) in rv.json.get('message')


def test_unpaid_filing(session, client, jwt):
    identifier = 'CP7654321'
    business = factory_business(identifier)

    filing_json = FILING_HEADER
    filing_json['specialResolution'] = SPECIAL_RESOLUTION
    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {}


base_url = 'https://LEGAL_API_BASE_URL'

@pytest.mark.parametrize('test_name, filing_name_1, legal_filing_1, filing_name_2, legal_filing_2, status, expected_msg, expected_http_code', [
        ('special_res_paper', 'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PAPER_ONLY, {}, HTTPStatus.NOT_FOUND),
        ('special_res_pending', 'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PENDING, {}, HTTPStatus.NOT_FOUND),
        ('special_res_paid', 'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PAID, 
         {'documents': {'primary': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution',
                        'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt'}},
        HTTPStatus.OK),
        ('special_res_completed', 'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.COMPLETED,
         {'documents': {'primary': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution',
                        'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                        'legalFilings': [
                            {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'},
                        ]
                        }
         },
        HTTPStatus.OK),
        ('specres_court_completed', 'specialResolution', SPECIAL_RESOLUTION, 'courtOrder', COURT_ORDER, Filing.Status.COMPLETED,
         {'documents': {'primary': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution',
                        'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                        'legalFilings': [
                            {'courtOrder': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/courtOrder'},
                            {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'},
                        ]
                        }
         },
        HTTPStatus.OK),
    ])
def test_various_filing_states(session, client, jwt, 
                               test_name,
                               filing_name_1, legal_filing_1, 
                               filing_name_2, legal_filing_2,
                               status, expected_msg, expected_http_code):
    """Test document list based on filing states."""
    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name_1
    filing_json['filing'][filing_name_1] = legal_filing_1

    if legal_filing_2:
        filing_json['filing'][filing_name_2] = legal_filing_2

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = status
    filing.save()

    if status == 'COMPLETED':
        lf = [list(x.keys()) for x in filing.legal_filings()]
        legal_filings = [item for sublist in lf for item in sublist]
        filing._meta_data = {'legalFilings': legal_filings}
        filing.save()

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], business.identifier))
    
    # remove the filing ID
    rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))
    expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))

    assert rv.status_code == expected_http_code
    assert rv_data == expected


def test_get_receipt(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    filing_name = 'incorporationApplication'
    payment_id = '12345'

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing'][filing_name] = INCORPORATION
    filing_json['filing'].pop('business')

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = 'PAID'
    filing._payment_token = payment_id
    filing.save()
    filing_core = Filing()
    filing_core._storage = filing

    requests_mock.post(f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
                       json={'foo': 'bar'},
                       status_code=HTTPStatus.CREATED)

    token = helper_create_jwt(jwt, roles=[STAFF_ROLE], username='username')

    content, status_code = _get_receipt(business, filing_core, token)

    assert status_code == HTTPStatus.CREATED
    assert requests_mock.called_once


def test_get_receipt_request_mock(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    filing_name = 'incorporationApplication'
    payment_id = '12345'

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing'][filing_name] = INCORPORATION
    filing_json['filing'].pop('business')

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = 'PAID'
    filing._payment_token = payment_id
    filing.save()

    requests_mock.post(f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
                       json={'foo': 'bar'},
                       status_code=HTTPStatus.CREATED)

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filing.id}/documents/receipt',
                    headers=create_header(jwt,
                                          [STAFF_ROLE],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    assert rv.status_code == HTTPStatus.CREATED
    assert requests_mock.called_once
