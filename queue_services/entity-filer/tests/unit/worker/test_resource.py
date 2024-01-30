import base64
import copy
import random
from http import HTTPStatus

import pytest
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from registry_schemas.example_data import SPECIAL_RESOLUTION, FILING_HEADER

from tests.unit import create_business, create_filing


def create_cloud_event_envelope(ce, message_id: str = 10):
    cloud_event_envelope = {
        "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
        "message": {
            "data": base64.b64encode(to_queue_message(ce)).decode("UTF-8"),
            "messageId": message_id,
            "attributes": {},
        },
        "id": 1,
    }
    return cloud_event_envelope


def test_error_not_msg(client):
    """Return a 4xx when an no JSON present."""

    rv = client.post("/")

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert "no cloud event" in rv.text


def test_error_not_valid_msg(client):
    """Return a 4xx when an no JSON present."""

    ce = SimpleCloudEvent(
        id="fake-id",
        source="fake-for-tests",
        subject="fake-subject",
        type="filingMessage",
        data={},
    )

    rv = client.post("/", json=create_cloud_event_envelope(ce))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert "no filing info in cloud event" in rv.text


def test_missing_filing(client, session):
    """Return a 4xx when an no JSON present."""

    ce = SimpleCloudEvent(
        id="fake-id",
        source="fake-for-tests",
        subject="fake-subject",
        type="filingMessage",
        data={
            "filingMessage": {
                "filingIdentifier": 12345,
            }
        },
    )

    rv = client.post("/", json=create_cloud_event_envelope(ce))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert "Unable to process filing: FilingMessage" in rv.text


def test_process_simple_filing(client, session):
    """Return a 4xx when an no JSON present."""

    # Setup
    identifier = "BC1234567"
    main_legal_filing = "specialResolution"
    legal_type = "BC"

    filing_submission = copy.deepcopy(FILING_HEADER)
    filing_submission["filing"][main_legal_filing] = copy.deepcopy(SPECIAL_RESOLUTION)
    filing_submission["filing"]["header"]["name"] = main_legal_filing
    filing_submission["filing"]["business"]["legalType"] = legal_type
    filing_submission["filing"]["business"]["identifier"] = identifier

    business = create_business(identifier, legal_type=legal_type)

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    filing_id = (create_filing(payment_id, filing_submission, business_id=business.id)).id

    ce = SimpleCloudEvent(
        id="fake-id",
        source="fake-for-tests",
        subject="fake-subject",
        type="filingMessage",
        data={
            "filingMessage": {
                "filingIdentifier": filing_id,
            }
        },
    )

    # Test
    rv = client.post("/", json=create_cloud_event_envelope(ce))

    # Validate Test
    assert rv.status_code == HTTPStatus.OK
    assert "{}" in rv.text
