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
from simple_cloudevent import SimpleCloudEvent

from business_digital_credentials.exceptions import QueueException
from business_digital_credentials.resources.business_digital_credentials import bp, process_event
from business_model.models.types.filings import FilingTypes


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


# Tests for process_event function

@patch("business_digital_credentials.digital_credential_processors.business_number.process")
@patch("business_model.models.Business.find_by_identifier")
def test_process_event_business_number_message(mock_find_business, mock_bn_process, app):
    """Test process_event with business number message."""
    with app.app_context():
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        mock_find_business.return_value = mock_business
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "bc.registry.business.bn"
        ce.data = {"identifier": "BC1234567"}
        
        process_event(ce)
        
        mock_find_business.assert_called_once_with("BC1234567")
        mock_bn_process.assert_called_once_with(mock_business)


@patch("business_digital_credentials.digital_credential_processors.admin_revoke.process")
@patch("business_model.models.Business.find_by_identifier")
def test_process_event_admin_revoke_message(mock_find_business, mock_admin_process, app):
    """Test process_event with admin revoke message."""
    with app.app_context():
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        mock_find_business.return_value = mock_business
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "bc.registry.admin.revoke"
        ce.data = {"identifier": "BC1234567"}
        
        process_event(ce)
        
        mock_find_business.assert_called_once_with("BC1234567")
        mock_admin_process.assert_called_once_with(mock_business)


@patch("business_digital_credentials.digital_credential_processors.change_of_registration.process")
@patch("business_model.models.Business.find_by_internal_id")
@patch("business_model.models.Filing.find_by_id")
def test_process_event_filing_message_change_of_registration(mock_find_filing, mock_find_business, mock_cor_process, app):
    """Test process_event with filingMessage for change of registration."""
    with app.app_context():
        mock_filing = MagicMock()
        mock_filing.filing_type = FilingTypes.CHANGEOFREGISTRATION.value
        mock_filing.status = "COMPLETED"
        mock_filing.business_id = 123
        mock_find_filing.return_value = mock_filing
        
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        mock_find_business.return_value = mock_business
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"filingIdentifier": 999}}
        
        process_event(ce)
        
        mock_find_filing.assert_called_once_with(999)
        mock_find_business.assert_called_once_with(123)
        mock_cor_process.assert_called_once_with(mock_business, mock_filing)


@patch("business_digital_credentials.digital_credential_processors.dissolution.process")
@patch("business_model.models.Business.find_by_internal_id")
@patch("business_model.models.Filing.find_by_id")
def test_process_event_filing_message_dissolution(mock_find_filing, mock_find_business, mock_dissolution_process, app):
    """Test process_event with filingMessage for dissolution."""
    with app.app_context():
        mock_filing = MagicMock()
        mock_filing.filing_type = FilingTypes.DISSOLUTION.value
        mock_filing.filing_sub_type = "voluntary"
        mock_filing.status = "COMPLETED"
        mock_filing.business_id = 123
        mock_find_filing.return_value = mock_filing
        
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        mock_find_business.return_value = mock_business
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"filingIdentifier": 999}}
        
        process_event(ce)
        
        mock_find_filing.assert_called_once_with(999)
        mock_find_business.assert_called_once_with(123)
        mock_dissolution_process.assert_called_once_with(mock_business, "voluntary")


@patch("business_digital_credentials.digital_credential_processors.put_back_on.process")
@patch("business_model.models.Business.find_by_internal_id")
@patch("business_model.models.Filing.find_by_id")
def test_process_event_filing_message_put_back_on(mock_find_filing, mock_find_business, mock_pbo_process, app):
    """Test process_event with filingMessage for put back on."""
    with app.app_context():
        mock_filing = MagicMock()
        mock_filing.filing_type = FilingTypes.PUTBACKON.value
        mock_filing.status = "COMPLETED"
        mock_filing.business_id = 123
        mock_find_filing.return_value = mock_filing
        
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        mock_find_business.return_value = mock_business
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"filingIdentifier": 999}}
        
        process_event(ce)
        
        mock_find_filing.assert_called_once_with(999)
        mock_find_business.assert_called_once_with(123)
        mock_pbo_process.assert_called_once_with(mock_business, mock_filing)


def test_process_event_filing_message_unsupported_filing_type(app, caplog):
    """Test process_event with filingMessage for unsupported filing type."""
    with app.app_context():
        mock_filing = MagicMock()
        mock_filing.filing_type = "UNSUPPORTED_TYPE"
        mock_filing.status = "COMPLETED"
        mock_filing.business_id = 123
        
        mock_business = MagicMock()
        mock_business.identifier = "BC1234567"
        mock_business.legal_name = "Test Business"
        
        with patch("business_model.models.Filing.find_by_id", return_value=mock_filing), \
             patch("business_model.models.Business.find_by_internal_id", return_value=mock_business):
            
            ce = MagicMock(spec=SimpleCloudEvent)
            ce.type = "filingMessage"
            ce.data = {"filingMessage": {"filingIdentifier": 999}}
            
            process_event(ce)
            
            # Assert - should log and not raise exception
            assert "Unsupported filing type: UNSUPPORTED_TYPE" in caplog.text


def test_process_event_unsupported_event_type(app, caplog):
    """Test process_event with unsupported event type."""
    with app.app_context():
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "unsupported.event.type"
        ce.data = {"some": "data"}
        
        result = process_event(ce)
        
        # Assert - should log and return None
        assert result is None
        assert "Unsupported event type: unsupported.event.type" in caplog.text


def test_process_event_missing_data(app):
    """Test process_event with missing data."""
    with app.app_context():
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = None
        
        # Act & Assert
        with pytest.raises(QueueException, match="Digital credential message is missing data"):
            process_event(ce)


def test_process_event_filing_message_missing_filing_message(app):
    """Test process_event with filingMessage missing filingMessage key."""
    with app.app_context():
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"wrongKey": "wrongValue"}
        
        # Act & Assert
        with pytest.raises(QueueException, match="Digital credential message is missing filingMessage"):
            process_event(ce)


def test_process_event_filing_message_missing_filing_identifier(app):
    """Test process_event with filingMessage missing filingIdentifier."""
    with app.app_context():
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"wrongKey": "wrongValue"}}
        
        # Act & Assert
        with pytest.raises(QueueException, match="Digital credential message is missing filingIdentifier"):
            process_event(ce)


def test_process_event_business_message_missing_identifier(app):
    """Test process_event with business message missing identifier."""
    with app.app_context():
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "bc.registry.business.bn"
        ce.data = {"wrongKey": "wrongValue"}
        
        # Act & Assert
        with pytest.raises(QueueException, match="Digital credential message is missing identifier"):
            process_event(ce)


@patch("business_model.models.Filing.find_by_id")
def test_process_event_filing_not_found(mock_find_filing, app):
    """Test process_event when filing is not found."""
    with app.app_context():
        mock_find_filing.return_value = None
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"filingIdentifier": 999}}
        
        # Act & Assert
        with pytest.raises(QueueException, match="Filing not found for id: 999"):
            process_event(ce)


@patch("business_model.models.Filing.find_by_id")
def test_process_event_filing_not_completed(mock_find_filing, app):
    """Test process_event when filing is not completed."""
    with app.app_context():
        mock_filing = MagicMock()
        mock_filing.status = "PENDING"
        mock_find_filing.return_value = mock_filing
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "filingMessage"
        ce.data = {"filingMessage": {"filingIdentifier": 999}}
        
        # Act & Assert
        with pytest.raises(QueueException, match="Filing with id: 999 processing not complete"):
            process_event(ce)


@patch("business_model.models.Business.find_by_identifier")
def test_process_event_business_not_found_by_identifier(mock_find_business, app):
    """Test process_event when business is not found by identifier."""
    with app.app_context():
        mock_find_business.return_value = None
        
        ce = MagicMock(spec=SimpleCloudEvent)
        ce.type = "bc.registry.business.bn"
        ce.data = {"identifier": "BC1234567"}
        
        # Act & Assert
        with pytest.raises(Exception, match="Business with identifier: BC1234567 not found"):
            process_event(ce)
