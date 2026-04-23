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
"""Tests for helpers in business_emailer.email_processors package __init__."""
import pytest
import requests_mock

from business_emailer.email_processors import (
    get_account_by_affiliated_identifier,
    get_entity_dashboard_url,
    get_org_id_for_temp_identifier,
)


@pytest.fixture
def auth_url(app):
    """Set AUTH_URL / AUTH_WEB_URL to dummy values for the duration of a test."""
    original_api = app.config.get('AUTH_URL')
    original_web = app.config.get('AUTH_WEB_URL')
    app.config['AUTH_URL'] = 'https://auth-api-url'
    app.config['AUTH_WEB_URL'] = 'https://auth-web-url/'
    yield app.config['AUTH_URL']
    app.config['AUTH_URL'] = original_api
    app.config['AUTH_WEB_URL'] = original_web


def test_get_account_by_affiliated_identifier_returns_json(app, auth_url):
    """Assert the affiliated-account JSON is returned when the auth response is valid JSON."""
    identifier = 'BC1234567'
    token = 'token'
    expected = {'orgs': [{'id': 42, 'name': 'Acme'}]}
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json=expected, status_code=200)
        result = get_account_by_affiliated_identifier(identifier, token)

        assert result == expected
        assert m.last_request.headers['Authorization'] == f'Bearer {token}'
        assert m.last_request.headers['Accept'] == 'application/json'


def test_get_account_by_affiliated_identifier_returns_none_on_bad_json(app, auth_url):
    """Assert None is returned when the auth response body is not valid JSON."""
    identifier = 'BC1234567'
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, text='not json', status_code=200)
        result = get_account_by_affiliated_identifier(identifier, 'token')

        assert result is None


def test_get_org_id_for_temp_identifier_returns_first_org_id(app, auth_url):
    """Assert the first org id is returned when orgs are present."""
    identifier = 'T12345'
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json={'orgs': [{'id': 99}, {'id': 100}]}, status_code=200)
        assert get_org_id_for_temp_identifier(identifier, 'token') == 99


@pytest.mark.parametrize('identifier,response_json', [
    ('T12345', {'orgs': []}),
    ('BC1234567', {'orgs': []}),
    ('T12345', {}),
])
def test_get_org_id_for_temp_identifier_raises_when_no_orgs(app, auth_url, identifier, response_json):
    """Assert Exception is raised when orgs are missing or empty (both T and non-T identifiers)."""
    url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(url, json=response_json, status_code=200)
        with pytest.raises(Exception):
            get_org_id_for_temp_identifier(identifier, 'token')


def test_get_entity_dashboard_url_non_temp_uses_dashboard_url(app, auth_url, config):
    """Assert non-temp identifiers return DASHBOARD_URL + identifier and make no HTTP calls."""
    identifier = 'BC1234567'
    with app.app_context(), requests_mock.Mocker() as m:
        url = get_entity_dashboard_url(identifier, 'token')
        assert url == config.get('DASHBOARD_URL') + identifier
        assert m.call_count == 0


def test_get_entity_dashboard_url_temp_uses_auth_web_url(app, auth_url):
    """Assert temp identifiers resolve to AUTH_WEB_URL + account/<org_id>/business."""
    identifier = 'T12345'
    orgs_url = f'{auth_url}/orgs?affiliation={identifier}'

    with app.app_context(), requests_mock.Mocker() as m:
        m.get(orgs_url, json={'orgs': [{'id': 77}]}, status_code=200)
        url = get_entity_dashboard_url(identifier, 'token')
        assert url == 'https://auth-web-url/account/77/business'
