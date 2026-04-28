# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for business_emailer.services.namex.NameXService."""
from unittest.mock import patch

import pytest
import requests_mock
from business_account.AccountService import AccountService

from business_emailer.services.namex import NameXService


@pytest.fixture
def namex_url(app):
    """Set NAMEX_SVC_URL to a dummy value for the duration of a test."""
    original = app.config.get("NAMEX_SVC_URL")
    app.config["NAMEX_SVC_URL"] = "https://namex-svc-url/"
    yield app.config["NAMEX_SVC_URL"]
    app.config["NAMEX_SVC_URL"] = original


def test_query_nr_number_returns_response(app, namex_url):
    """Assert the namex GET is issued with the bearer token and response returned as-is."""
    identifier = "NR 1234567"
    token = "token"

    with app.app_context(), \
            patch.object(AccountService, "get_bearer_token", return_value=token), \
            requests_mock.Mocker() as m:
        m.get(f"{namex_url}requests/{identifier}", json={"id": 1}, status_code=200)
        response = NameXService.query_nr_number(identifier)

        assert response.status_code == 200
        assert response.json() == {"id": 1}
        assert m.last_request.headers["Authorization"] == f"Bearer {token}"
        assert m.last_request.headers["Content-Type"] == "application/json"


def test_query_nr_number_returns_non_200_as_is(app, namex_url):
    """Assert non-OK responses are returned to the caller unchanged (no raise)."""
    identifier = "NR 9999999"

    with app.app_context(), \
            patch.object(AccountService, "get_bearer_token", return_value="token"), \
            requests_mock.Mocker() as m:
        m.get(f"{namex_url}requests/{identifier}", status_code=404)
        response = NameXService.query_nr_number(identifier)

        assert response.status_code == 404
