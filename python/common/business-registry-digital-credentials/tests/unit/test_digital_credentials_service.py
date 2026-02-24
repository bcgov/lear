# Copyright © 2026 Province of British Columbia
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
"""Tests for digital credentials service.

Test suite to ensure the DigitalCredentialsService works as expected.
"""

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from business_model.models import DCDefinition, DCRevocationReason
from business_registry_digital_credentials.digital_credentials import DigitalCredentialsService


def _make_valid_token():
    """Create a valid JWT token with future expiry."""
    return pyjwt.encode({"exp": int(time.time()) + 3600}, "secret", algorithm="HS256")


class TestInit:
    """Tests for __init__."""

    def test_defaults_to_none(self):
        """All attributes default to None."""
        service = DigitalCredentialsService()
        assert service.app is None
        assert service.api_url is None
        assert service.api_token is None
        assert service.public_schema_did is None
        assert service.public_issuer_did is None
        assert service.business_schema_name is None
        assert service.business_schema_version is None
        assert service.business_schema_id is None
        assert service.business_cred_def_id is None
        assert service.wallet_cred_def_id is None


class TestInitApp:
    """Tests for init_app."""

    @patch.object(DigitalCredentialsService, "_register_business_definition")
    def test_sets_config_values(self, mock_register, app):
        """init_app reads config values from the app."""
        app.config["TRACTION_API_URL"] = "https://traction.test"
        app.config["TRACTION_PUBLIC_SCHEMA_DID"] = "schema-did"
        app.config["TRACTION_PUBLIC_ISSUER_DID"] = "issuer-did"
        app.config["BUSINESS_SCHEMA_NAME"] = "test-schema"
        app.config["BUSINESS_SCHEMA_VERSION"] = "1.0"
        app.config["BUSINESS_SCHEMA_ID"] = "schema-id"
        app.config["BUSINESS_CRED_DEF_ID"] = "cred-def-id"
        app.config["WALLET_CRED_DEF_ID"] = "wallet-cred-def-id"

        service = DigitalCredentialsService()
        service.init_app(app)

        assert service.app is app
        assert service.api_url == "https://traction.test"
        assert service.public_schema_did == "schema-did"
        assert service.public_issuer_did == "issuer-did"
        assert service.business_schema_name == "test-schema"
        assert service.business_schema_version == "1.0"
        assert service.business_schema_id == "schema-id"
        assert service.business_cred_def_id == "cred-def-id"
        assert service.wallet_cred_def_id == "wallet-cred-def-id"

    @patch.object(DigitalCredentialsService, "_register_business_definition", side_effect=Exception("fail"))
    def test_suppresses_registration_error(self, mock_register, app):
        """init_app suppresses errors from _register_business_definition."""
        service = DigitalCredentialsService()
        service.init_app(app)
        assert service.app is app


class TestGetHeaders:
    """Tests for _get_headers."""

    def test_returns_auth_headers(self, app):
        """Returns correct content type and bearer token."""
        app.api_token = "test-token"
        service = DigitalCredentialsService()
        service.app = app
        headers = service._get_headers()
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-token",
        }


class TestCreateInvitation:
    """Tests for create_invitation."""

    @patch("business_registry_digital_credentials.digital_credentials.requests.post")
    def test_success(self, mock_post, app):
        """Returns invitation JSON on success."""
        app.api_token = _make_valid_token()
        mock_post.return_value.json.return_value = {"invitation": {"@id": "123"}}
        mock_post.return_value.raise_for_status = MagicMock()

        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.create_invitation()

        assert result == {"invitation": {"@id": "123"}}

    @patch("business_registry_digital_credentials.digital_credentials.requests.post", side_effect=Exception("fail"))
    def test_returns_none_on_error(self, mock_post, app):
        """Returns None when request fails."""
        app.api_token = _make_valid_token()
        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.create_invitation()
        assert result is None


class TestFetchCredentialExchangeRecord:
    """Tests for fetch_credential_exchange_record."""

    @patch("business_registry_digital_credentials.digital_credentials.requests.get")
    def test_success(self, mock_get, app):
        """Returns record JSON on success."""
        app.api_token = _make_valid_token()
        mock_get.return_value.json.return_value = {"cred_ex_id": "123"}
        mock_get.return_value.raise_for_status = MagicMock()

        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.fetch_credential_exchange_record("123")
        assert result == {"cred_ex_id": "123"}


class TestRemoveConnectionRecord:
    """Tests for remove_connection_record."""

    @patch("business_registry_digital_credentials.digital_credentials.requests.delete")
    def test_success(self, mock_delete, app):
        """Returns response JSON on success."""
        app.api_token = _make_valid_token()
        mock_delete.return_value.json.return_value = {}
        mock_delete.return_value.raise_for_status = MagicMock()

        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.remove_connection_record("conn-123")
        assert result == {}

    @patch("business_registry_digital_credentials.digital_credentials.requests.delete", side_effect=Exception("fail"))
    def test_returns_none_on_error(self, mock_delete, app):
        """Returns None when request fails."""
        app.api_token = _make_valid_token()
        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.remove_connection_record("conn-123")
        assert result is None


class TestRemoveCredentialExchangeRecord:
    """Tests for remove_credential_exchange_record."""

    @patch("business_registry_digital_credentials.digital_credentials.requests.delete")
    def test_success(self, mock_delete, app):
        """Returns response JSON on success."""
        app.api_token = _make_valid_token()
        mock_delete.return_value.json.return_value = {}
        mock_delete.return_value.raise_for_status = MagicMock()

        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.remove_credential_exchange_record("cred-123")
        assert result == {}


class TestRevokeCredential:
    """Tests for revoke_credential."""

    @patch("business_registry_digital_credentials.digital_credentials.requests.post")
    def test_success(self, mock_post, app):
        """Returns response JSON on success."""
        app.api_token = _make_valid_token()
        mock_post.return_value.json.return_value = {}
        mock_post.return_value.raise_for_status = MagicMock()

        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.revoke_credential("conn-123", "cred-rev-1", "rev-reg-1", DCRevocationReason.UPDATED_INFORMATION)
        assert result == {}

    @patch("business_registry_digital_credentials.digital_credentials.requests.post", side_effect=Exception("fail"))
    def test_returns_none_on_error(self, mock_post, app):
        """Returns None when request fails."""
        app.api_token = _make_valid_token()
        service = DigitalCredentialsService()
        service.app = app
        service.api_url = "https://traction.test"
        result = service.revoke_credential("conn-123", "cred-rev-1", "rev-reg-1", DCRevocationReason.UPDATED_INFORMATION)
        assert result is None
