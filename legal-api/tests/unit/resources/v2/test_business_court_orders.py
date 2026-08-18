# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the business-court-orders end-point.

Test-Suite to ensure that the /businesses../court-orders endpoint is working as expected.
"""
import copy
from http import HTTPStatus
import pytest

from business_model.models import CourtOrder, Document, DocumentType
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from registry_schemas.example_data import FILING_TEMPLATE
from tests.unit.models import factory_business, factory_completed_filing
from tests.unit.services.utils import create_header


def test_get_business_court_orders(app, session, client, jwt, requests_mock):
    """Assert that business court orders are returned."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    filing_dict = copy.deepcopy(FILING_TEMPLATE)
    filing_dict['filing']['header']['name'] = 'courtOrder'
    filing = factory_completed_filing(business, filing_dict)

    court_order = CourtOrder(
        file_number='123456',
        order_date='2021-01-31T00:00:00+00:00',
        effect_of_order='planOfArrangement',
        business_id=business.id,
        filing_id=filing.id
    )
    court_order.save()

    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    rv = client.get(f'/api/v2/businesses/{identifier}/court-orders',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert 'courtOrders' in rv.json
    assert len(rv.json['courtOrders']) == 1
    assert rv.json['courtOrders'][0]['fileNumber'] == '123456'


def test_get_business_court_order_by_id(app, session, client, jwt, requests_mock):
    """Assert that a specific business court order is returned."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    filing_dict = copy.deepcopy(FILING_TEMPLATE)
    filing_dict['filing']['header']['name'] = 'courtOrder'
    filing = factory_completed_filing(business, filing_dict)

    court_order = CourtOrder(
        file_number='123456',
        order_date='2021-01-31T00:00:00+00:00',
        effect_of_order='planOfArrangement',
        business_id=business.id,
        filing_id=filing.id
    )
    court_order.save()

    file_key='test_file_key.pdf'
    file_name='test_file.pdf'
    document = Document(
        filing_id=filing.id,
        business_id=business.id,
        type=DocumentType.COURT_ORDER.value,
        file_key=file_key,
        file_name=file_name
    )
    document.save()

    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    rv = client.get(f'/api/v2/businesses/{identifier}/court-orders/{court_order.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert 'courtOrder' in rv.json
    assert rv.json['courtOrder']['fileNumber'] == '123456'
    assert 'files' in rv.json['courtOrder']
    assert len(rv.json['courtOrder']['files']) == 1
    assert rv.json['courtOrder']['files'][0]['fileName'] == file_name
    assert rv.json['courtOrder']['files'][0]['fileKey'] == file_key
    assert rv.json['courtOrder']['files'][0]['url'].endswith(
        f'api/v2/businesses/{identifier}/filings/{filing.id}/documents/static/{file_key}')


def test_get_business_court_orders_not_found(app, session, client, jwt, requests_mock):
    """Assert that 404 is returned if business is not found."""
    identifier = 'CP7654321'

    rv = client.get(f'/api/v2/businesses/{identifier}/court-orders',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_get_business_court_order_by_id_not_found(app, session, client, jwt, requests_mock):
    """Assert that 404 is returned if court order is not found."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    rv = client.get(f'/api/v2/businesses/{identifier}/court-orders/99999',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} court order not found'}
