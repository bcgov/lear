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

"""Tests to assure the RequestContext service.

Test-Suite to ensure that RequestContext and its helpers work as expected.
"""
import pytest
from flask import g

from legal_api.services.request_context import add_account_linking_key_header, build_from_flask, get_request_context
from tests.unit.services.utils import helper_create_jwt_json_token_claims


@pytest.fixture(autouse=True)
def isolate_request_context(monkeypatch):
    """Isolate flask.g for each test in this module.

    The `app` fixture is session scoped and keeps a single app context open for the whole run,
    Use monkeypatch so g is restored to its initial state after each test.
    """
    monkeypatch.setattr(g, 'jwt_oidc_token_info', None, raising=False)
    g.pop('request_context', None)
    yield
    g.pop('request_context', None)


@pytest.mark.parametrize('headers,expected', [
    ({'Account-Linking-Key': 'test-linking-key'}, 'test-linking-key'),
    ({}, None),
])
def test_build_from_flask_account_linking_key(app, headers, expected):
    """Assert that build_from_flask reads the Account-Linking-Key header when present."""
    with app.test_request_context(headers=headers):
        rc = build_from_flask()
        assert rc.account_linking_key == expected


def test_get_request_context_backwards_compatible(app, session, monkeypatch):
    """Assert get_request_context() behaves as before when no Account-Linking-Key header is present."""
    token_info = helper_create_jwt_json_token_claims(username='test-user')
    with app.test_request_context(headers={'Account-Id': '1234'}):
        monkeypatch.setattr(g, 'jwt_oidc_token_info', token_info, raising=False)
        rc = get_request_context()
        assert rc.account_id == '1234'
        assert rc.user is not None
        assert rc.user.username == 'test-user'
        assert rc.account_linking_key is None


def test_add_account_linking_key_header_present(app):
    """Assert that the header is forwarded onto a headers dict when present on the request."""
    with app.test_request_context(headers={'Account-Linking-Key': 'test-linking-key'}):
        headers = {'Authorization': 'Bearer token'}
        add_account_linking_key_header(headers)
        assert headers == {'Authorization': 'Bearer token', 'Account-Linking-Key': 'test-linking-key'}


def test_add_account_linking_key_header_absent(app):
    """Assert that no header is added onto a headers dict when absent on the request."""
    with app.test_request_context():
        headers = {'Authorization': 'Bearer token'}
        add_account_linking_key_header(headers)
        assert headers == {'Authorization': 'Bearer token'}

