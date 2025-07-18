# Copyright © 2025 Province of British Columbia
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
"""Test configuration and fixtures."""

import pytest
from unittest.mock import Mock
from flask import Flask


@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.app_context():
        yield app


@pytest.fixture
def session(app):
    """Create a database session for testing."""
    # For now, return a mock since we don't have actual database setup
    # In a real app, you'd create and return a proper database session
    return Mock()


@pytest.fixture
def mock_business():
    """Create a mock business for testing."""
    business = Mock()
    business.id = 1
    business.identifier = "BC1234567"
    business.legal_name = "Test Business Inc."
    business.legal_type = "BC"
    return business


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock()
    user.id = 1
    user.username = "testuser"
    user.firstname = "Test"
    user.lastname = "User"
    user.login_source = "BCSC"
    return user


@pytest.fixture
def mock_jwt_manager():
    """Create a mock JWT manager for testing."""
    jwt = Mock()
    jwt.contains_role = Mock(return_value=False)
    return jwt


@pytest.fixture
def mock_jwt_token_info():
    """Create mock JWT token info."""
    return {"sub": "test-subject", "preferred_username": "testuser", "given_name": "Test", "family_name": "User"}
