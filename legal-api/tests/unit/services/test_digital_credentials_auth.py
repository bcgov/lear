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

import pytest

from business_model.models.business import Business
from business_model.models.user import User
from business_registry_digital_credentials import DigitalCredentialsRulesService
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from legal_api.services.digital_credentials_auth import (
    DBC_ENABLED_BUSINESS_TYPES_FLAG,
    _resolve_allowed_business_types,
    are_digital_credentials_allowed,
    get_digital_credentials_preconditions,
)
from tests.unit.services.utils import create_business, jwt_request_context

token_json = {'username': 'test'}


@pytest.fixture
def mock_flags():
    """Patch the flags accessor so tests stub the flag client instead of standing one up.

    Yields the stub flags object — set ``mock_flags.is_on.return_value`` and
    ``mock_flags.value.return_value`` per test.
    """
    with patch('legal_api.services.digital_credentials_auth._get_flags') as get_flags:
        flags = MagicMock()
        get_flags.return_value = flags
        yield flags


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed(mock_rule, mock_user, app, session, jwt):
    with jwt_request_context(app, jwt, [PUBLIC_USER], token_json['username']):
        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is True


@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_no_token(mock_rule, app, session, jwt):
    with jwt_request_context(app, jwt, [PUBLIC_USER], token_json['username']):
        app.app_ctx_globals_class.jwt_oidc_token_info = {'idp_userid': None}

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('business_model.models.User.find_by_jwt_token', return_value=None)
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_no_user(mock_rule, mock_jwt, app, session, jwt):
    with jwt_request_context(app, jwt, [PUBLIC_USER], token_json['username']):
        app.app_ctx_globals_class.jwt_oidc_token_info = token_json

        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_false_when_user_is_staff(mock_rule, mock_jwt, app, session, jwt):
    with jwt_request_context(app, jwt, [STAFF_ROLE], token_json['username']):
        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1, username='testuser'))
@patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=['proprietor', 'director'])
def test_get_digital_credentials_preconditions(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'username': 'test'}
        business = Business()
        business.legal_name = 'Test Business'
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": "testuser",
            "attestRoles": ["proprietor", "director"],
        }


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1, username='testuser'))
@patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=['proprietor', 'director'])
def test_get_digital_credentials_preconditions_business_no_name(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'username': 'test'}
        business = Business()
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": None,
            "attestName": "testuser",
            "attestRoles": ["proprietor", "director"],
        }


@patch('business_model.models.User.find_by_jwt_token', return_value=None)
@patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=[])
def test_get_digital_credentials_preconditions_no_user(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'username': 'test'}
        business = Business()
        business.legal_name = 'Test Business'
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": None,
            "attestRoles": [],
        }


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1, username='testuser'))
@patch.object(DigitalCredentialsRulesService, 'get_preconditions', return_value=[])
def test_get_digital_credentials_preconditions_none(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'username': 'test'}
        business = Business()
        business.legal_name = 'Test Business'
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": "testuser",
            "attestRoles": [],
        }


@patch('business_model.models.User.find_by_jwt_token', return_value=None)
def test_get_digital_credentials_preconditions_no_user(mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {'username': 'test'}
        business = Business()
        result = get_digital_credentials_preconditions(business)
        assert result == {}


# ----------------------------------------------------------------------------
# _resolve_allowed_business_types — exercises the legal-api-owned FF resolution.
# ----------------------------------------------------------------------------


def test_resolve_allowed_business_types_flag_off(mock_flags, app):
    """Flag OFF → returns empty list (DBC disabled)."""
    mock_flags.is_on.return_value = False

    with app.app_context():
        assert _resolve_allowed_business_types() == []

    mock_flags.is_on.assert_called_once_with(DBC_ENABLED_BUSINESS_TYPES_FLAG, None, None)
    mock_flags.value.assert_not_called()


def test_resolve_allowed_business_types_valid(mock_flags, app):
    """Flag ON with a valid ``{"types": [...]}`` dict → returns the list."""
    mock_flags.is_on.return_value = True
    mock_flags.value.return_value = {"types": ["SP", "BEN", "GP"]}

    with app.app_context():
        assert _resolve_allowed_business_types() == ["SP", "BEN", "GP"]

    mock_flags.value.assert_called_once_with(DBC_ENABLED_BUSINESS_TYPES_FLAG, None, None)


def test_resolve_allowed_business_types_valid_empty_list(mock_flags, app):
    """Flag ON with empty types list → returns empty list (caller filters in/out)."""
    mock_flags.is_on.return_value = True
    mock_flags.value.return_value = {"types": []}

    with app.app_context():
        assert _resolve_allowed_business_types() == []


@pytest.mark.parametrize("bad_value", [
    "not-a-dict",
    123,
    None,
    [],
    {},                              # missing "types" key
    {"type": ["SP"]},                # wrong key name
    {"types": "SP"},                 # types not a list
    {"types": 123},                  # types not a list
    {"types": None},                 # types not a list
])
def test_resolve_allowed_business_types_malformed(mock_flags, app, bad_value):
    """Malformed flag payloads → empty list, no exception."""
    mock_flags.is_on.return_value = True
    mock_flags.value.return_value = bad_value

    with app.app_context():
        assert _resolve_allowed_business_types() == []


# ----------------------------------------------------------------------------
# Wrapper integration: are_digital_credentials_allowed threads the resolved
# FF value through to the shared API.
# ----------------------------------------------------------------------------


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_passes_resolved_flag_to_rules(
    mock_rules, mock_user, mock_flags, app, session, jwt,
):
    """The wrapper resolves the FF and forwards the list into the shared rules check."""
    mock_flags.is_on.return_value = True
    mock_flags.value.return_value = {"types": ["SP", "BEN", "GP"]}

    with jwt_request_context(app, jwt, [PUBLIC_USER], token_json['username']):
        business = create_business('SP', Business.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is True

    # Shared rules service called as rules.are_digital_credentials_allowed(user, business, allowed_business_types).
    args, _ = mock_rules.call_args
    assert args[-1] == ["SP", "BEN", "GP"]


@patch('business_model.models.User.find_by_jwt_token', return_value=User(id=1))
@patch.object(DigitalCredentialsRulesService, 'are_digital_credentials_allowed', return_value=True)
def test_are_digital_credentials_allowed_passes_empty_list_when_flag_off(
    mock_rules, mock_user, mock_flags, app, session, jwt,
):
    """When the FF is off, the wrapper still calls the rules check — with ``[]``."""
    mock_flags.is_on.return_value = False

    with jwt_request_context(app, jwt, [PUBLIC_USER], token_json['username']):
        business = create_business('SP', Business.State.ACTIVE)
        are_digital_credentials_allowed(business, jwt)

    args, _ = mock_rules.call_args
    assert args[-1] == []
