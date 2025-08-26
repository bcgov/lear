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

from unittest.mock import patch

from business_model.models import Business
from business_model.models import User
from business_registry_digital_credentials.digital_credentials_auth import get_digital_credentials_preconditions
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
