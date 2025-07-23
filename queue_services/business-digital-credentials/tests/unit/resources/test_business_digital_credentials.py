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
"""Tests for business_digital_credentials resource."""
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from business_digital_credentials.resources.business_digital_credentials import bp


@pytest.fixture
def test_client():
    """Create a test client with just the blueprint registered."""
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app.test_client()


@patch("business_digital_credentials.resources.business_digital_credentials.verify_gcp_jwt")
@patch("business_digital_credentials.resources.business_digital_credentials.process_event")
@patch("business_digital_credentials.services.gcp_queue.get_simple_cloud_event")
def test_worker_success(mock_get_cloud_event, mock_process_event, mock_verify_gcp_jwt, test_client):
    """Test successful worker processing."""
    # Mock successful authentication
    mock_verify_gcp_jwt.return_value = ""
    
    # Mock cloud event
    mock_ce = MagicMock()
    mock_get_cloud_event.return_value = mock_ce
    
    response = test_client.post("/", data=b"test_data")

    assert response.status_code == HTTPStatus.OK
    mock_verify_gcp_jwt.assert_called_once()
    mock_get_cloud_event.assert_called_once()
    mock_process_event.assert_called_once_with(mock_ce)


@patch("business_digital_credentials.resources.business_digital_credentials.verify_gcp_jwt")
@patch("business_digital_credentials.resources.business_digital_credentials.process_event")
@patch("business_digital_credentials.services.gcp_queue.get_simple_cloud_event")
def test_worker_no_event(mock_get_cloud_event, mock_process_event, mock_verify_gcp_jwt, test_client):
    """Test worker when no cloud event is returned."""
    # Mock successful authentication
    mock_verify_gcp_jwt.return_value = ""
    
    # Mock no cloud event
    mock_get_cloud_event.return_value = None
    
    response = test_client.post("/", data=b"test_data")
    
    assert response.status_code == HTTPStatus.OK
    mock_verify_gcp_jwt.assert_called_once()
    mock_get_cloud_event.assert_called_once()
    mock_process_event.assert_not_called()


@patch("business_digital_credentials.resources.business_digital_credentials.verify_gcp_jwt")
@patch("business_digital_credentials.resources.business_digital_credentials.process_event")
@patch("business_digital_credentials.services.gcp_queue.get_simple_cloud_event")
def test_worker_queue_exception(mock_get_cloud_event, mock_process_event, mock_verify_gcp_jwt, test_client):
    """Test worker when QueueException is raised during processing."""
    from business_digital_credentials.exceptions import QueueException
    
    # Mock successful authentication
    mock_verify_gcp_jwt.return_value = ""
    
    # Mock cloud event and QueueException being raised during processing
    mock_ce = MagicMock()
    mock_get_cloud_event.return_value = mock_ce
    mock_process_event.side_effect = QueueException("Queue error", 400)
    
    response = test_client.post("/", data=b"test_data")
    
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.get_json() == {}
    mock_verify_gcp_jwt.assert_called_once()
    mock_get_cloud_event.assert_called_once()
    mock_process_event.assert_called_once_with(mock_ce)


@patch("business_digital_credentials.resources.business_digital_credentials.verify_gcp_jwt")
@patch("business_digital_credentials.resources.business_digital_credentials.process_event")
@patch("business_digital_credentials.services.gcp_queue.get_simple_cloud_event")
def test_worker_authentication_failure(mock_get_cloud_event, mock_process_event, mock_verify_gcp_jwt, test_client):
    """Test worker when authentication fails."""
    # Mock authentication failure
    mock_verify_gcp_jwt.return_value = "Invalid token"
    
    response = test_client.post("/", data=b"test_data")
    
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.get_json() == {}
    mock_verify_gcp_jwt.assert_called_once()
    mock_get_cloud_event.assert_not_called()
    mock_process_event.assert_not_called()
