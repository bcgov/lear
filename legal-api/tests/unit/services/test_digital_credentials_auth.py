# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for digital credentials auth functions.

Test suite to ensure that auth functions for digital credentials are working as expected
"""

from unittest.mock import MagicMock, patch
import jwt as pyjwt

from legal_api.models.business import Business
from legal_api.models.user import User
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from legal_api.services.digital_credentials_auth import are_digital_credentials_allowed
from legal_api.services.digital_credentials_rules import DigitalCredentialsRulesService
from tests.unit.services.utils import create_business, helper_create_jwt

token_json = {'username': 'test'}


@patch('legal_api.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed(mock_rule, mock_user, monkeypatch, app, session, jwt):
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = token_json
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is True


@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_no_token(mock_rule, monkeypatch, app, session, jwt):
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'idp_userid': None}
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token', return_value=None)
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_no_user(mock_rule, mock_jwt, monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = token_json
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_user_is_staff(mock_rule, mock_jwt, monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[STAFF_ROLE], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = token_json
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False
