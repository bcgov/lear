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

"""Tests to assure the business-share-classes end-point.

Test-Suite to ensure that the /businesses../share-classes endpoint is working as expected.
"""
import pytest
from http import HTTPStatus

from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from tests.unit.models import factory_business, factory_share_class
from tests.unit.services.utils import create_header


@pytest.mark.parametrize('test_name,role', [
    ('public-user', PUBLIC_USER),
    ('account-identity', ACCOUNT_IDENTITY),
    ('staff', STAFF_ROLE),
    ('system', SYSTEM_ROLE)
])
def test_get_business_share_classes(app, session, client, jwt, requests_mock, test_name, role):
    """Assert that business share classes are returned."""
    identifier = 'CP1234567'
    share_class = factory_share_class(identifier)

    # mock response from auth to give view access (not needed if staff / system)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [role], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'shareClasses' in rv.json
    assert rv.json == {'shareClasses': [share_class.json]}


def test_get_business_no_share_classes(session, client, jwt):
    """Assert that business share classes are not returned."""
    # setup
    identifier = 'CP7654321'
    factory_business(identifier)

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['shareClasses'] == []


def test_get_business_share_class_by_id(session, client, jwt):
    """Assert that business share class is returned."""
    # setup
    identifier = 'CP7654321'
    share_class = factory_share_class(identifier)
    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes/{share_class.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['shareClass'] == share_class.json


def test_get_business_share_class_by_invalid_id(session, client, jwt):
    """Assert that business share class is not returned."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    share_class_id = 10000
    business.save()

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes/{share_class_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} share class not found'}


def test_get_share_classes_invalid_business(session, client, jwt):
    """Assert that business is not returned."""
    # setup
    identifier = 'CP7654321'

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_get_share_classes_unauthorized(app, session, client, jwt, requests_mock):
    """Assert that share classes are not returned for an unauthorized user."""
    # setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    business.save()

    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': []})

    # test
    rv = client.get(f'/api/v2/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [PUBLIC_USER], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
    assert rv.json == {'message': f'You are not authorized to view share classes for {identifier}.'}
