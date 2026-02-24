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

from business_model.models import Business
from business_model.models import User
from business_registry_digital_credentials.digital_credentials_auth import (
    are_digital_credentials_allowed,
    get_digital_credentials_preconditions,
)
from business_registry_digital_credentials.digital_credentials_rules import DigitalCredentialsRulesService

STAFF_ROLE = "staff"
PUBLIC_USER = "public_user"
token_json = {"username": "test"}


@patch("business_model.models.User.find_by_jwt_token", return_value=User(id=1, username="testuser"))
@patch.object(DigitalCredentialsRulesService, "get_preconditions", return_value=["proprietor", "director"])
def test_get_digital_credentials_preconditions(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        business = Business()
        business.legal_name = "Test Business"
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": "testuser",
            "attestRoles": ["proprietor", "director"],
        }


@patch("business_model.models.User.find_by_jwt_token", return_value=User(id=1, username="testuser"))
@patch.object(DigitalCredentialsRulesService, "get_preconditions", return_value=["proprietor", "director"])
def test_get_digital_credentials_preconditions_business_no_name(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        business = Business()
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": None,
            "attestName": "testuser",
            "attestRoles": ["proprietor", "director"],
        }


@patch("business_model.models.User.find_by_jwt_token", return_value=None)
@patch.object(DigitalCredentialsRulesService, "get_preconditions", return_value=[])
def test_get_digital_credentials_preconditions_no_user(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        business = Business()
        business.legal_name = "Test Business"
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": None,
            "attestRoles": [],
        }


@patch("business_model.models.User.find_by_jwt_token", return_value=User(id=1, username="testuser"))
@patch.object(DigitalCredentialsRulesService, "get_preconditions", return_value=[])
def test_get_digital_credentials_preconditions_none(mock_preconditions, mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        business = Business()
        business.legal_name = "Test Business"
        result = get_digital_credentials_preconditions(business)
        assert result == {
            "attestBusiness": "Test Business",
            "attestName": "testuser",
            "attestRoles": [],
        }


@patch("business_model.models.User.find_by_jwt_token", return_value=None)
def test_get_digital_credentials_preconditions_no_user(mock_user, app):
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        business = Business()
        result = get_digital_credentials_preconditions(business)
        assert result == {}


# Tests for are_digital_credentials_allowed


def test_are_digital_credentials_allowed_staff(app):
    """Staff users are not allowed digital credentials."""
    with app.test_request_context():
        jwt_mock = MagicMock()
        jwt_mock.contains_role.return_value = True
        business = Business()
        assert are_digital_credentials_allowed(business, jwt_mock) is False


@patch("business_model.models.User.find_by_jwt_token", return_value=None)
def test_are_digital_credentials_allowed_no_user(mock_find, app):
    """Returns False when user is not found."""
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        jwt_mock = MagicMock()
        jwt_mock.contains_role.return_value = False
        business = Business()
        assert are_digital_credentials_allowed(business, jwt_mock) is False


@patch("business_model.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch.object(DigitalCredentialsRulesService, "are_digital_credentials_allowed", return_value=True)
def test_are_digital_credentials_allowed_delegates_to_rules(mock_rules, mock_find, app):
    """Delegates to rules service when user is found."""
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        jwt_mock = MagicMock()
        jwt_mock.contains_role.return_value = False
        business = Business()
        assert are_digital_credentials_allowed(business, jwt_mock) is True


@patch("business_model.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch.object(DigitalCredentialsRulesService, "are_digital_credentials_allowed", return_value=False)
def test_are_digital_credentials_allowed_rules_deny(mock_rules, mock_find, app):
    """Returns False when rules service denies access."""
    with app.test_request_context():
        app.app_ctx_globals_class.jwt_oidc_token_info = {"username": "test"}
        jwt_mock = MagicMock()
        jwt_mock.contains_role.return_value = False
        business = Business()
        assert are_digital_credentials_allowed(business, jwt_mock) is False
