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

"""Tests to assure the business-resolutions end-point.

Test-Suite to ensure that the /businesses../resolutions endpoint is working as expected.
"""
from http import HTTPStatus

from legal_api.models import Resolution
from legal_api.services.authz import STAFF_ROLE
from tests.unit.models import factory_legal_entity
from tests.unit.services.utils import create_header


def test_get_business_resolutions(session, client, jwt):
    """Assert that business resolutions are returned."""
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    resolution_1 = Resolution(
        resolution_date='2020-02-02',
        resolution_type='ORDINARY',
        legal_entity_id=legal_entity.id
    )
    resolution_2 = Resolution(
        resolution_date='2020-03-03',
        resolution_type='SPECIAL',
        legal_entity_id=legal_entity.id
    )
    resolution_1.save()
    resolution_2.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'resolutions' in rv.json
    assert len(rv.json['resolutions']) == 2


def test_get_business_no_resolutions(session, client, jwt):
    """Assert that business resolutions are not returned."""
    # setup
    identifier = 'CP7654321'
    factory_legal_entity(identifier)

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['resolutions'] == []


def test_get_business_resolution_by_id(session, client, jwt):
    """Assert that business resolution is returned."""
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    resolution_1 = Resolution(
        resolution_date='2020-02-02',
        resolution_type='ORDINARY',
        legal_entity_id=legal_entity.id
    )
    resolution_2 = Resolution(
        resolution_date='2020-03-03',
        resolution_type='SPECIAL',
        legal_entity_id=legal_entity.id
    )
    resolution_1.save()
    resolution_2.save()
    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions/{resolution_1.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert rv.json['resolution']['date'] == '2020-02-02'


def test_get_business_resolution_by_invalid_id(session, client, jwt):
    """Assert that business resolution is not returned."""
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    resolution_id = 5000
    legal_entity.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions/{resolution_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} resolution not found'}


def test_get_business_resolution_by_type(session, client, jwt):
    """Assert that business resolutions matching the type are returned."""
    # setup
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    resolution_1 = Resolution(
        resolution_date='2020-02-02',
        resolution_type='ORDINARY',
        legal_entity_id=legal_entity.id
    )
    resolution_2 = Resolution(
        resolution_date='2020-03-03',
        resolution_type='SPECIAL',
        legal_entity_id=legal_entity.id
    )
    resolution_1.save()
    resolution_2.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions?type=special',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'resolutions' in rv.json
    assert len(rv.json['resolutions']) == 1
    assert rv.json['resolutions'][0]['date'] == '2020-03-03'


def test_get_business_resolution_by_invalid_type(session, client, jwt):
    """Assert that business resolutions are not returned."""
    # setup
    identifier = 'CP7654321'
    legal_entity =factory_legal_entity(identifier)
    resolution_1 = Resolution(
        resolution_date='2020-02-02',
        resolution_type='ORDINARY',
        legal_entity_id=legal_entity.id
    )
    resolution_2 = Resolution(
        resolution_date='2020-03-03',
        resolution_type='SPECIAL',
        legal_entity_id=legal_entity.id
    )
    resolution_1.save()
    resolution_2.save()

    # test
    rv = client.get(f'/api/v1/businesses/{identifier}/resolutions?type=invalid',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )
    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'resolutions' in rv.json
    assert rv.json['resolutions'] == []
