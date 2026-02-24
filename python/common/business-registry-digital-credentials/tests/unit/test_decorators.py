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
"""Tests for digital credentials decorators.

Test suite to ensure decorators work as expected.
"""

import time
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from business_registry_digital_credentials.decorators import (
    _get_traction_token,
    can_access_digital_credentials,
    requires_traction_auth,
)


def _make_valid_token():
    """Create a valid JWT token with future expiry."""
    return pyjwt.encode({"exp": int(time.time()) + 3600}, "secret", algorithm="HS256")


def _make_expired_token():
    """Create an expired JWT token."""
    return pyjwt.encode({"exp": int(time.time()) - 3600}, "secret", algorithm="HS256")


class TestCanAccessDigitalCredentials:
    """Tests for can_access_digital_credentials decorator."""

    def test_business_not_found(self, app):
        """Returns 404 when business is not found."""

        @can_access_digital_credentials
        def dummy_view(**kwargs):
            return "ok", 200

        with app.test_request_context():
            with patch("business_registry_digital_credentials.decorators.Business.find_by_identifier", return_value=None):
                result, status = dummy_view(identifier="BC1234567")
        assert status == HTTPStatus.NOT_FOUND

    @patch("business_registry_digital_credentials.decorators.are_digital_credentials_allowed", return_value=False)
    def test_not_allowed(self, mock_allowed, app):
        """Returns 401 when digital credentials are not allowed."""

        @can_access_digital_credentials
        def dummy_view(**kwargs):
            return "ok", 200

        business = MagicMock()
        with app.test_request_context():
            with patch(
                "business_registry_digital_credentials.decorators.Business.find_by_identifier", return_value=business
            ):
                result, status = dummy_view(identifier="BC1234567")
        assert status == HTTPStatus.UNAUTHORIZED

    @patch("business_registry_digital_credentials.decorators.are_digital_credentials_allowed", return_value=True)
    def test_allowed(self, mock_allowed, app):
        """Calls through to wrapped function when allowed."""

        @can_access_digital_credentials
        def dummy_view(**kwargs):
            return "ok", 200

        business = MagicMock()
        with app.test_request_context():
            with patch(
                "business_registry_digital_credentials.decorators.Business.find_by_identifier", return_value=business
            ):
                result, status = dummy_view(identifier="BC1234567")
        assert result == "ok"
        assert status == 200


class TestRequiresTractionAuth:
    """Tests for requires_traction_auth decorator."""

    def test_valid_token_passes_through(self, app):
        """Function is called when token is valid."""
        app.api_token = _make_valid_token()

        @requires_traction_auth
        def dummy_func():
            return "result"

        result = dummy_func()
        assert result == "result"

    @patch("business_registry_digital_credentials.decorators._get_traction_token", return_value="new-token")
    def test_no_token_fetches_new(self, mock_get_token, app):
        """Fetches new token when no token exists."""

        @requires_traction_auth
        def dummy_func():
            return "result"

        # Remove api_token if it exists
        if hasattr(app, "api_token"):
            delattr(app, "api_token")

        result = dummy_func()
        assert result == "result"
        mock_get_token.assert_called_once()

    @patch("business_registry_digital_credentials.decorators._get_traction_token", return_value="new-token")
    def test_expired_token_fetches_new(self, mock_get_token, app):
        """Fetches new token when existing token is expired."""
        app.api_token = _make_expired_token()

        @requires_traction_auth
        def dummy_func():
            return "result"

        result = dummy_func()
        assert result == "result"
        mock_get_token.assert_called_once()


class TestGetTractionToken:
    """Tests for _get_traction_token."""

    def test_missing_api_url(self, app):
        """Raises EnvironmentError when TRACTION_API_URL is not set."""
        with pytest.raises(EnvironmentError, match="TRACTION_API_URL"):
            _get_traction_token()

    def test_missing_tenant_id(self, app):
        """Raises EnvironmentError when TRACTION_TENANT_ID is not set."""
        app.config["TRACTION_API_URL"] = "https://traction.test"
        with pytest.raises(EnvironmentError, match="TRACTION_TENANT_ID"):
            _get_traction_token()

    def test_missing_api_key(self, app):
        """Raises EnvironmentError when TRACTION_API_KEY is not set."""
        app.config["TRACTION_API_URL"] = "https://traction.test"
        app.config["TRACTION_TENANT_ID"] = "tenant-id"
        with pytest.raises(EnvironmentError, match="TRACTION_API_KEY"):
            _get_traction_token()

    @patch("business_registry_digital_credentials.decorators.requests.get")
    @patch("business_registry_digital_credentials.decorators.requests.post")
    def test_success(self, mock_post, mock_get, app):
        """Returns token on successful authentication."""
        app.config["TRACTION_API_URL"] = "https://traction.test"
        app.config["TRACTION_TENANT_ID"] = "tenant-id"
        app.config["TRACTION_API_KEY"] = "api-key"

        valid_token = _make_valid_token()
        mock_post.return_value.json.return_value = {"token": valid_token}
        mock_post.return_value.raise_for_status = MagicMock()
        mock_get.return_value.status_code = 200
        mock_get.return_value.raise_for_status = MagicMock()

        result = _get_traction_token()
        assert result == valid_token
