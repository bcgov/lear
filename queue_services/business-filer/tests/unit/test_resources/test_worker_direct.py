
import copy
import logging
import asyncio
import base64
import random
import uuid
from datetime import datetime
from datetime import timezone
from http import HTTPStatus

import pytest
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from registry_schemas.example_data import CP_SPECIAL_RESOLUTION_TEMPLATE
from tests.unit import create_entity, create_filing

def create_gcp_filing_msg(filing_id):
    """Create the GCP filing payload."""
    filing_msg = {"filingMessage": {"filingIdentifier": filing_id}}
    return filing_msg

def create_filer_cloud_event(filing_id: str):
    ce = SimpleCloudEvent(
        id=str(uuid.uuid4()),
        source='business_pay',
        subject='filing',
        time=datetime.now(timezone.utc),
        type='filingMessage',
        data = {"filingMessage": {"filingIdentifier": filing_id}}
    )
    return ce


def create_test_envelope(ce: SimpleCloudEvent):
    #
    # This needs to mimic the envelope created by GCP PubSb when call a resource
    #
    envelope = {
        "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
        "message": {
            "data": base64.b64encode(to_queue_message(ce)).decode("UTF-8"),
            "messageId": "10",
            "attributes": {},
        },
        "id": 1,
    }
    return envelope

def test_worker_no_msg(client, caplog):
    """Test worker endpoint with no message."""
    with caplog.at_level(logging.DEBUG):
        response = client.post('/')
        assert response.status_code == 200

        assert "No incoming raw msg." in caplog.text


def test_worker_msg_not_validated(client, caplog):
    """Test worker endpoint with no filing."""
    filing_id = 0
    ce = create_filer_cloud_event(filing_id=filing_id)
    envelope = create_test_envelope(ce)
    response = client.post('/', json=envelope)
    assert response.status_code == 403


def test_worker_msg_validated(client, app, caplog, mocker):
    """Test worker endpoint validated filing."""

    # Mock the JWT callback for GCP
    claim = {
        "email_verified": app.config.get("SUB_SERVICE_ACCOUNT", "test@test.test"),
        "email": app.config.get("SUB_SERVICE_ACCOUNT", "test@test.test"),
    }
    mocker.patch("google.oauth2.id_token.verify_oauth2_token", return_value=claim)
    headers = {
        "Authorization": f"Bearer doesn't matter",
        "Content-Type": "application/json",
    }

    filing_id = 0
    ce = create_filer_cloud_event(filing_id=filing_id)
    envelope = create_test_envelope(ce)
    response = client.post('/', json=envelope, headers=headers)
    assert response.status_code == 500


def test_worker_msg(client, app, caplog, mocker):
    """Test worker endpoint validated filing."""

    # Setup
    identifier = f'CP{random.randint(1000000, 9999999)}'
    business = create_entity(identifier, "CP", f"{identifier} Limited")
    business_id = business.id
    filing = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
    del filing['filing']['changeOfName']
    filing['filing']['business']['identifier'] = identifier
    payment_id = str(random.randint(1000000, 9999999))
    filing_id = (create_filing(payment_id, filing, business_id=business_id)).id

    # Mock the JWT callback for GCP
    claim = {
        "email_verified": app.config.get("SUB_SERVICE_ACCOUNT", "test@test.test"),
        "email": app.config.get("SUB_SERVICE_ACCOUNT", "test@test.test"),
    }
    mocker.patch("google.oauth2.id_token.verify_oauth2_token", return_value=claim)
    headers = {
        "Authorization": f"Bearer doesn't matter",
        "Content-Type": "application/json",
    }

    ce = create_filer_cloud_event(filing_id=filing_id)
    envelope = create_test_envelope(ce)

    # Test
    response = client.post('/', json=envelope, headers=headers)

    assert response.status_code == 200

