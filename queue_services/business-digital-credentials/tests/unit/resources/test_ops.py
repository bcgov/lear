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
"""Tests for ops resource."""
from http import HTTPStatus

import pytest
from flask import Flask

from business_digital_credentials.resources.ops import bp


@pytest.fixture
def test_client():
    """Create a test client with ops blueprint registered."""
    app = Flask(__name__)
    app.register_blueprint(bp, url_prefix="/ops")
    return app.test_client()


def test_get_healthz(test_client):
    """Test the healthz endpoint."""
    response = test_client.get("/ops/healthz")
    
    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {"message": "api is healthy"}


def test_get_readyz(test_client):
    """Test the readyz endpoint."""
    response = test_client.get("/ops/readyz")
    
    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == {"message": "api is ready"}
