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

"""Tests to assure the filing-comment endpoint.

Test-Suite to ensure that the businesses/<identifier>/comments endpoint is working as expected.
"""
import copy
from http import HTTPStatus

from freezegun import freeze_time
from registry_schemas.example_data import COMMENT_BUSINESS

from legal_api.models import User
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils import datetime
from tests.unit.models import factory_legal_entity, factory_legal_entity_comment
from tests.unit.services.utils import create_header


# prep sample post data for single comment
SAMPLE_JSON_DATA = copy.deepcopy(COMMENT_BUSINESS)
del SAMPLE_JSON_DATA['comment']['timestamp']


def test_get_all_business_comments_no_results(session, client, jwt):
    """Assert that endpoint returns no-results correctly."""
    identifier = 'CP7654321'
    factory_legal_entity(identifier)

    rv = client.get(f'/api/v1/businesses/{identifier}/comments',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert 0 == len(rv.json.get('comments'))


def test_get_all_business_comments_only_one(session, client, jwt):
    """Assert that a list of comments with a single comment is returned correctly."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    factory_legal_entity_comment(b)

    rv = client.get(f'/api/v1/businesses/{identifier}/comments',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.OK == rv.status_code
    assert 1 == len(rv.json.get('comments'))


def test_get_all_business_comments_multiple(session, client, jwt):
    """Assert that multiple comments are returned correctly."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    factory_legal_entity_comment(b)
    factory_legal_entity_comment(b, 'other text')

    rv = client.get(f'/api/v1/businesses/{identifier}/comments',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.OK == rv.status_code
    assert 2 == len(rv.json.get('comments'))


def test_get_one_business_comment_by_id(session, client, jwt):
    """Assert that a single comment is returned correctly."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    c = factory_legal_entity_comment(b, 'some specific text')

    rv = client.get(f'/api/v1/businesses/{identifier}/comments/{c.id}',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.OK == rv.status_code
    assert 'some specific text' == rv.json.get('comment').get('comment')


def test_business_comment_json_output(session, client, jwt):
    """Assert the json output of a comment is correctly formatted."""
    identifier = 'CP7654321'
    b = factory_legal_entity(identifier)
    u = User(username='username', firstname='firstname', lastname='lastname', sub='sub', iss='iss', idp_userid='123', login_source='IDIR')
    u.save()

    now = datetime.datetime(1970, 1, 1, 0, 0).replace(tzinfo=datetime.timezone.utc)
    with freeze_time(now):
        factory_legal_entity_comment(b, 'some specific text', u)

        rv = client.get(f'/api/v1/businesses/{identifier}/comments',
                        headers=create_header(jwt, [STAFF_ROLE]))

        assert HTTPStatus.OK == rv.status_code
        assert 'some specific text' == rv.json.get('comments')[0].get('comment').get('comment')
        assert 'firstname lastname' == rv.json.get('comments')[0].get('comment').get('submitterDisplayName')
        assert now.isoformat() == rv.json.get('comments')[0].get('comment').get('timestamp')


def test_get_comments_invalid_business_error(session, client, jwt):
    """Assert that error is returned when business doesn't exist."""
    factory_legal_entity('CP1111111')

    rv = client.get('/api/v1/businesses/CP2222222/comments',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.NOT_FOUND == rv.status_code
    assert 'CP2222222 not found' == rv.json.get('message')


def test_get_business_comment_invalid_commentid_error(session, client, jwt):
    """Assert that error is returned when comment ID doesn't exist."""
    b = factory_legal_entity('CP1111111')

    rv = client.get(f'/api/v1/businesses/{b.identifier}/comments/1',
                    headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.NOT_FOUND == rv.status_code
    assert 'Comment 1 not found' == rv.json.get('message')


def test_post_business_comment(session, client, jwt):
    """Assert that a simple post of a comment succeeds."""
    b = factory_legal_entity('CP1111111')

    json_data = copy.deepcopy(SAMPLE_JSON_DATA)
    json_data['comment']['businessId'] = b.identifier

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.CREATED == rv.status_code


def test_post_comment_missing_business_id_error(session, client, jwt):
    """Assert that the post fails when missing filing ID in json (null and missing)."""
    b = factory_legal_entity('CP1111111')

    # test null business ID
    json_data = copy.deepcopy(SAMPLE_JSON_DATA)
    json_data['comment']['businessId'] = None

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code

    # test missing business ID
    json_data = copy.deepcopy(SAMPLE_JSON_DATA)
    del json_data['comment']['businessId']

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code


def test_post_business_comment_missing_text_error(session, client, jwt):
    """Assert that the post fails when business missing comment text in json (null and missing)."""
    b = factory_legal_entity('CP1111111')

    # test null comment text
    json_data = copy.deepcopy(SAMPLE_JSON_DATA)
    json_data['comment']['comment'] = None

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code

    # test missing comment text
    json_data = copy.deepcopy(SAMPLE_JSON_DATA)
    del json_data['comment']['comment']

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.UNPROCESSABLE_ENTITY == rv.status_code


def test_post_business_comment_basic_user_error(session, client, jwt):
    """Assert that the post fails when sent from Basic (non-staff) user."""
    b = factory_legal_entity('CP1111111')

    json_data = copy.deepcopy(SAMPLE_JSON_DATA)

    rv = client.post(f'/api/v1/businesses/{b.identifier}/comments',
                     json=json_data,
                     headers=create_header(jwt, [BASIC_USER]))

    assert HTTPStatus.UNAUTHORIZED == rv.status_code


def test_post_comment_invalid_business_error(session, client, jwt):
    """Assert that error is returned when business doesn't exist."""
    factory_legal_entity('CP1111111')

    json_data = copy.deepcopy(SAMPLE_JSON_DATA)

    rv = client.post('/api/v1/businesses/CP2222222/comments',
                     json=json_data,
                     headers=create_header(jwt, [STAFF_ROLE]))

    assert HTTPStatus.NOT_FOUND == rv.status_code
    assert 'CP2222222 not found' == rv.json.get('message')
