# Copyright © 2024 Province of British Columbia
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
"""Tests for the Digital Credentials Rules service.

Test suite to ensure that the Digital Credentials Rules service is working as expected.
"""

from unittest.mock import MagicMock, patch
import pytest
import jwt as pyjwt
from legal_api.models.business import Business
from legal_api.models.party import Party
from legal_api.models.user import User
from legal_api.services import DigitalCredentialsRulesService
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE, are_digital_credentials_allowed
from tests.unit.services.utils import create_business, helper_create_jwt


@pytest.fixture(scope='module')
def digital_credentials_rules():
    return DigitalCredentialsRulesService()


@pytest.mark.parametrize(
    'test_user, expected',
    [
        (Party(**{'first_name': 'First', 'last_name': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (Party(**{'first_name': 'First', 'middle_initial': 'M',
         'last_name': 'Last'}), {'first_name': 'first m', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'lastname': 'Last'}),
         {'first_name': 'first', 'last_name': 'last'}),
        (User(**{'firstname': 'First', 'middlename': 'M', 'lastname': 'Last'}),
         {'first_name': 'first m', 'last_name': 'last'}),
        (User(), {'first_name': '', 'last_name': ''}),
        (Party(), {'first_name': '', 'last_name': ''}),
    ]
)
def test_formatted_user(app, session, digital_credentials_rules, test_user, expected):
    """Assert that the user is formatted correctly."""

    assert digital_credentials_rules.formatted_user(test_user) == expected


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_no_token(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=None)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=None)
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_no_user(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_user_is_staff(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[STAFF_ROLE], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='NOT_BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_login_source_not_bcsc(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_false_when_wrong_business_type(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('GP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=False)
def test_are_digital_credentials_allowed_false_when_not_owner_operator(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('legal_api.models.User.find_by_jwt_token',
       return_value=User(id=1, login_source='BCSC'))
@patch('legal_api.services.digital_credentials_rules.DigitalCredentialsRulesService.is_self_registered_owner_operator',
       return_value=True)
def test_are_digital_credentials_allowed_true(monkeypatch, app, session, jwt):
    token_json = {'username': 'test'}
    token = helper_create_jwt(
        jwt, roles=[PUBLIC_USER], username=token_json['username'])
    headers = {'Authorization': 'Bearer ' + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr('flask.request.headers.get', mock_auth)

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is True
