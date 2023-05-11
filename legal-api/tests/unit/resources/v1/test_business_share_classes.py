# Copyright © 2020 Province of British Columbia
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
from http import HTTPStatus

from legal_api.services.authz import STAFF_ROLE
from tests.unit.models import factory_legal_entity, factory_share_class
from tests.unit.services.utils import create_header


def test_get_business_share_classes(session, client, jwt):
    """Assert that business share classes are returned."""
    identifier = 'CP1234567'
    share_class = factory_share_class(identifier)

    rv = client.get(f'/api/v1/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'shareClasses' in rv.json
    assert rv.json == {'shareClasses': [share_class.json]}


def test_get_business_no_share_classes(session, client, jwt):
    """Assert that business share classes are not returned."""
    # setup
    identifier = 'CP7654321'
    factory_legal_entity(identifier)

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/share-classes',
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
    rv = client.get(f'/api/v1/businesses/{identifier}/share-classes/{share_class.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['shareClass'] == share_class.json


def test_get_business_share_class_by_invalid_id(session, client, jwt):
    """Assert that business share class is not returned."""
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    share_class_id = 10000
    legal_entity.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/share-classes/{share_class_id}',
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
    rv = client.get(f'/api/v1/businesses/{identifier}/share-classes',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}
