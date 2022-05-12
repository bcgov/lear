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

"""Tests to assure the business-summary end-point.

Test-Suite to ensure that the /businesses../summary endpoint works as expected.
"""

from flask import current_app
from http import HTTPStatus


from legal_api.services.authz import STAFF_ROLE
from tests import integration_reports
from tests.unit.models import Address, PartyRole, factory_business, factory_party_role
from tests.unit.services.utils import create_header


@integration_reports
def test_get_document(requests_mock, session, client, jwt):
    """Assert that business summary is returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    requests_mock.post(current_app.config.get('REPORT_SVC_URL'), json={'foo': 'bar'})
    headers = create_header(jwt, [STAFF_ROLE], identifier, **{'accept': 'application/pdf'})
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary', headers=headers)
    # check
    assert rv.status_code == HTTPStatus.OK
    assert requests_mock.called_once
    assert requests_mock.last_request._request.headers.get('Content-Type') == 'application/json'


def test_get_document_invalid_business(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)

    # test
    rv = client.get(f'/api/v2/businesses/test/documents/summary',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_get_business_documents(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    docs_json = rv.json
    assert docs_json['documents']
    assert docs_json['documents']['summary']


def test_get_document_invalid_authorization(session, client, jwt):
    """Assert that business summary is not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/documents/summary')
    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
