# Copyright © 2020 Province of British Columbia
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

"""Tests to assure the AccountService.

Test-Suite to ensure that the AccountService is working as expected.
"""
import json
import os
import random
import uuid
from http import HTTPStatus

import pytest
import requests
from flask import current_app

from business_account import AccountService


def test_get_bearer_token(app, requests_mock):
    """Verifies the get_bearer_token returns the token as expected."""
    mock_token = "token"
    requests_mock.post(f"{app.config.get('ACCOUNT_SVC_AUTH_URL')}", json={"access_token": mock_token})
    with app.app_context():
        token = AccountService.get_bearer_token()

        assert token == mock_token


@pytest.mark.parametrize("test_num, user_token, idir_email, bcsc_email, expected_email", [
    ("1", "user-token", "idir@email.com", None, "idir@email.com"),
    ("2", "user-token", None, "bcsc@email.com", "bcsc@email.com"),
    ("3", "user-token", "idir@email.com", "bcsc@email.com", "bcsc@email.com"),
    ("4", None, None, "bcsc@email.com", "bcsc@email.com"),
])
def test_get_contacts(app, jwt, requests_mock, test_num, user_token, idir_email, bcsc_email, expected_email):
    """Verifies get_contacts returns as expected."""
    
    org_id = 1
    system_token = "system-token"
    auth_url = app.config.get("AUTH_SVC_URL")
    mock_org_data = {
        "mailingAddress": {
            "street": "101 Test Street"
        }
    }
    mock_user_data = {
        "firstname": "first",
        "lastname": "last",
        "email": idir_email,
        "contacts": [{"email": bcsc_email}] if bcsc_email else []
    }
    get_token_mock = requests_mock.post(f"{app.config.get('ACCOUNT_SVC_AUTH_URL')}", json={"access_token": system_token})
    get_user_data_mock = requests_mock.get(f"{auth_url}/users/@me", json=mock_user_data)
    get_org_contacts_mock = requests_mock.get(f"{auth_url}/orgs/{org_id}", json=mock_org_data)
    
    with app.app_context():
        contacts = AccountService.get_contacts(org_id, user_token)
    
        assert get_token_mock.called != bool(user_token)
        assert get_user_data_mock.called == True
        assert get_org_contacts_mock.called == True
        if user_token:
            assert user_token in get_user_data_mock.request_history[0].headers["Authorization"]
            assert user_token in get_org_contacts_mock.request_history[0].headers["Authorization"]
        else:
            assert system_token in get_user_data_mock.request_history[0].headers["Authorization"]
            assert system_token in get_org_contacts_mock.request_history[0].headers["Authorization"]

        assert contacts and len(contacts.get("contacts", [])) == 1
        contact_data = contacts["contacts"][0]
        assert contact_data["email"] == expected_email
        assert contact_data["firstName"] == mock_user_data["firstname"]
        assert contact_data["lastName"] == mock_user_data["lastname"]
        assert contact_data["street"] == mock_org_data["mailingAddress"]["street"]
