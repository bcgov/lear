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
"""Test suite for the decorators.py module in the legal_api package."""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, current_app

import legal_api.decorators as decorators

@pytest.fixture
def app_ctx():
    app = Flask(__name__)
    app.config['TRACTION_API_URL'] = 'http://traction-tenant-proxy-unit.test'
    app.config['TRACTION_TENANT_ID'] = 'abc-123-xyz-456'
    app.config['TRACTION_API_KEY'] = 'apikey'
    with app.app_context():
        yield app

def mock_token_response(token='sometoken', status_code=200):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'token': token}
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.return_value = None
    return mock_resp

def mock_check_response(status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.return_value = None
    return mock_resp

@patch('legal_api.decorators.pyjwt.decode')
@patch('legal_api.decorators.requests.get')
@patch('legal_api.decorators.requests.post')
def test_get_traction_token_success(mock_post, mock_get, mock_decode, app_ctx):
    mock_post.return_value = mock_token_response()
    mock_get.return_value = mock_check_response()
    mock_decode.return_value = {'exp': 9999999999}

    token = decorators._get_traction_token()
    assert token == 'sometoken'
    assert mock_post.called
    assert mock_get.called
    assert mock_decode.called

@patch('legal_api.decorators.pyjwt.decode')
@patch('legal_api.decorators.requests.get')
@patch('legal_api.decorators.requests.post')
def test_get_traction_token_401_retry_then_success(mock_post, mock_get, mock_decode, app_ctx):
    # First call returns 401, second call returns 200
    mock_post.return_value = mock_token_response()
    mock_decode.return_value = {'exp': 9999999999}
    mock_get.side_effect = [
        mock_check_response(status_code=401),
        mock_check_response(status_code=200)
    ]

    token = decorators._get_traction_token()
    assert token == 'sometoken'
    assert mock_get.call_count == 2

@patch('legal_api.decorators.pyjwt.decode')
@patch('legal_api.decorators.requests.get')
@patch('legal_api.decorators.requests.post')
def test_get_traction_token_invalid_token_error(mock_post, mock_get, mock_decode, app_ctx):
    mock_post.return_value = mock_token_response()
    mock_decode.side_effect = decorators.pyjwt.InvalidTokenError('bad token')

    with pytest.raises(EnvironmentError) as excinfo:
        decorators._get_traction_token()
    assert 'Failed to get Traction token' in str(excinfo.value)

@patch('legal_api.decorators.pyjwt.decode')
@patch('legal_api.decorators.requests.get')
@patch('legal_api.decorators.requests.post')
def test_get_traction_token_request_exception(mock_post, mock_get, mock_decode, app_ctx):
    mock_post.side_effect = decorators.requests.RequestException('network error')

    with pytest.raises(EnvironmentError) as excinfo:
        decorators._get_traction_token()
    assert 'Failed to get Traction token' in str(excinfo.value)

@pytest.mark.parametrize(
    "missing_key,expected_message",
    [
        ("TRACTION_API_URL", "TRACTION_API_URL environment variable is not set"),
        ("TRACTION_TENANT_ID", "TRACTION_TENANT_ID environment variable is not set"),
        ("TRACTION_API_KEY", "TRACTION_API_KEY environment variable is not set"),
    ]
)
def test_get_traction_token_missing_config_keys(app_ctx, missing_key, expected_message):
    del current_app.config[missing_key]
    with pytest.raises(EnvironmentError) as excinfo:
        decorators._get_traction_token()
    assert expected_message in str(excinfo.value)