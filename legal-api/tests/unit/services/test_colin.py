# Copyright © 2026 Province of British Columbia
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
"""Tests to assure the colin service."""
from http import HTTPStatus

import pytest
from requests import exceptions

from legal_api.services.cache import cache
from legal_api.services.colin import ColinService


PUBLIC_PATH = 'businesses/BC0870226/public'


@pytest.fixture(autouse=True)
def _clear_colin_cache(app):
    """Keep cached colin responses from leaking between tests."""
    cache.clear()


@pytest.fixture
def system_token(mocker):
    """Return the mocked system service token fetch."""
    return mocker.patch('legal_api.services.colin.AccountService.get_bearer_token', return_value='system-token')


def test_call_colin_api(app, requests_mock, system_token):
    """Assert the colin api is called with the configured url and the system token."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})

    json_data, status_code = ColinService.call_colin_api(PUBLIC_PATH)

    assert status_code == HTTPStatus.OK
    assert json_data == {'business': {}}
    assert colin_mock.last_request.headers['Authorization'] == 'Bearer system-token'


def test_call_colin_api_with_given_token(app, requests_mock, system_token):
    """Assert a given token is used as-is and the system token is not fetched."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})

    _, status_code = ColinService.call_colin_api(PUBLIC_PATH, token='user-token')

    assert status_code == HTTPStatus.OK
    assert colin_mock.last_request.headers['Authorization'] == 'Bearer user-token'
    system_token.assert_not_called()


def test_call_colin_api_without_token(app, requests_mock, mocker):
    """Assert no call is made when a token could not be fetched."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})
    mocker.patch('legal_api.services.colin.AccountService.get_bearer_token', return_value=None)

    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, None)
    assert not colin_mock.called


def test_call_colin_api_without_colin_url(app, requests_mock, system_token, mocker):
    """Assert an unconfigured COLIN_URL returns (None, None) instead of raising."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})
    mocker.patch.dict(app.config, {'COLIN_URL': ''})

    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, None)
    assert not colin_mock.called


def test_call_colin_api_non_json_body(app, requests_mock, system_token):
    """Assert a non-JSON body returns (None, status) and is never cached."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', text='<html>bad gateway</html>')

    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, HTTPStatus.OK)
    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, HTTPStatus.OK)

    assert colin_mock.call_count == 2


def test_call_colin_api_token_failure(app, mocker):
    """Assert a token-service outage returns (None, None) instead of raising."""
    mocker.patch('legal_api.services.colin.AccountService.get_bearer_token',
                 side_effect=exceptions.ConnectionError('keycloak down'))

    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, None)


def test_call_colin_api_connection_failure(app, requests_mock, system_token):
    """Assert a colin connection failure returns (None, None) instead of raising."""
    requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', exc=exceptions.ConnectTimeout)

    assert ColinService.call_colin_api(PUBLIC_PATH) == (None, None)


def test_call_colin_api_caches_definitive_responses(app, requests_mock, system_token):
    """Assert responses are cached per path - repeat calls don't hit colin again."""
    public_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})
    missing_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/businesses/BC0000000/public',
                                     status_code=HTTPStatus.NOT_FOUND, json={'message': 'not found'})

    assert ColinService.call_colin_api(PUBLIC_PATH) == ({'business': {}}, HTTPStatus.OK)
    assert ColinService.call_colin_api(PUBLIC_PATH) == ({'business': {}}, HTTPStatus.OK)
    # a 404 is a definitive answer too
    assert ColinService.call_colin_api('businesses/BC0000000/public')[1] == HTTPStatus.NOT_FOUND
    assert ColinService.call_colin_api('businesses/BC0000000/public')[1] == HTTPStatus.NOT_FOUND

    assert public_mock.call_count == 1
    assert missing_mock.call_count == 1


def test_call_colin_api_caches_per_token(app, requests_mock, system_token):
    """Assert a response cached under one token is not served to a call with another."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})

    ColinService.call_colin_api(PUBLIC_PATH)
    ColinService.call_colin_api(PUBLIC_PATH, token='user-token')
    ColinService.call_colin_api(PUBLIC_PATH, token='user-token')

    assert colin_mock.call_count == 2


def test_call_colin_api_does_not_cache_failures(app, requests_mock, system_token):
    """Assert an unavailable COLIN (5xx) is retried on the next call."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}',
                                   status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    assert ColinService.call_colin_api(PUBLIC_PATH)[1] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert ColinService.call_colin_api(PUBLIC_PATH)[1] == HTTPStatus.INTERNAL_SERVER_ERROR

    assert colin_mock.call_count == 2


def test_call_colin_api_cache_opt_out(app, requests_mock, system_token):
    """Assert use_cache=False bypasses the cache entirely - no stale reads, no writes."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})

    ColinService.call_colin_api(PUBLIC_PATH)  # populates the cache
    ColinService.call_colin_api(PUBLIC_PATH, use_cache=False)
    ColinService.call_colin_api(PUBLIC_PATH, use_cache=False)

    assert colin_mock.call_count == 3


def test_query_business(app, requests_mock, system_token):
    """Assert query_business goes through call_colin_api to the public endpoint."""
    colin_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/{PUBLIC_PATH}', json={'business': {}})

    json_data, status_code = ColinService.query_business('BC0870226')

    assert status_code == HTTPStatus.OK
    assert json_data == {'business': {}}
    assert colin_mock.last_request.headers['Authorization'] == 'Bearer system-token'

    # repeat calls are served from the cache unless the caller opts out
    ColinService.query_business('BC0870226')
    assert colin_mock.call_count == 1
    ColinService.query_business('BC0870226', use_cache=False)
    assert colin_mock.call_count == 2


def test_get_snapshot(app, requests_mock, system_token):
    """Assert get_snapshot goes through call_colin_api to the snapshot endpoint, with caching."""
    snapshot_mock = requests_mock.get(f'{app.config["COLIN_URL"]}/businesses/BC0870226/snapshot',
                                      json={'business': {'identifier': 'BC0870226'}})

    json_data, status_code = ColinService.get_snapshot('BC0870226')

    assert status_code == HTTPStatus.OK
    assert json_data['business']['identifier'] == 'BC0870226'
    # repeat calls are served from the cache
    assert ColinService.get_snapshot('BC0870226')[1] == HTTPStatus.OK
    assert snapshot_mock.call_count == 1
    # but a caller can opt out of the cache to force a fresh fetch
    assert ColinService.get_snapshot('BC0870226', use_cache=False)[1] == HTTPStatus.OK
    assert snapshot_mock.call_count == 2
