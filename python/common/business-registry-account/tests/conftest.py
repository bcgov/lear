# Copyright © 2019 Province of British Columbia
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
"""Common setup and fixtures for the pytest suite used by this service."""
from contextlib import contextmanager

import pytest
from flask import Flask

from business_account import AccountService
from business_account.config import TestConfig
from flask_jwt_oidc import JwtManager

_jwt = JwtManager()

@contextmanager
def not_raises(exception):
    """Corallary to the pytest raises builtin.

    Assures that an exception is NOT thrown.
    """
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}")


def setup_jwt_manager(app: Flask, jwt_manager: JwtManager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""
    def get_roles(a_dict):
        return a_dict["realm_access"]["roles"]  # pragma: no cover
    app.config["JWT_ROLE_CALLBACK"] = get_roles

    jwt_manager.init_app(app)


def create_app():
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(TestConfig)
    setup_jwt_manager(app, _jwt)

    return app

@pytest.fixture(scope="session")
def app():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app()

    return _app

@pytest.fixture(scope="function")
def account_service(app):
    with app.app_context():
        yield AccountService()


@pytest.fixture(scope="session")
def jwt():
    """Return a session-wide jwt manager."""
    return _jwt