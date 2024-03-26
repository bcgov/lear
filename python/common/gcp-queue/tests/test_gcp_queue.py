import base64
from contextlib import suppress

import flask
from gcp_queue import GcpQueue
import pytest
from simple_cloudevent import SimpleCloudEvent
from simple_cloudevent import to_queue_message
from simple_cloudevent import to_structured

BASE_ENVELOPE = {
    "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
    "message": {
        "data": "TWVzc2FnZSBudW1iZXIgMQ==",
        "messageId": "10",
        "attributes": {},
    },
    "id": 1,
}


@pytest.mark.parametrize(
    "test_name,msg,expected", [("invalid", {}, False), ("valid", BASE_ENVELOPE, True)]
)
def test_valid_envelope(test_name, msg, expected):
    """Test the validation the envelope."""
    rv = GcpQueue.is_valid_envelope(msg)

    assert rv is expected


@pytest.mark.parametrize(
    "test_name,queue_envelope,expected, ret_type",
    [("invalid", {}, None, type(None)), ("valid", BASE_ENVELOPE, BASE_ENVELOPE, dict)],
)
def test_get_envelope(mocker, test_name, queue_envelope, expected, ret_type):
    """Test the the envelope can be extracted from the request."""
    app = flask.Flask(__name__)
    with app.app_context():
        with app.test_request_context(content_type="application/json") as session:

            def mock_get_json():
                return queue_envelope

            mocker.patch.object(session.request, "get_json", mock_get_json)

            envelope = GcpQueue.get_envelope(session.request)

            assert isinstance(envelope, ret_type)
            assert envelope == expected


CLOUD_EVENT = SimpleCloudEvent(
    id="fake-id",
    source="fake-for-tests",
    subject="fake-subject",
    type="fake",
    data={"FilingId": 1, "PaymentId": 1, "SomeOtherNonsense": 1},
)
#
# This needs to mimic the envelope created by GCP PubSb when call a resource
#
WRAPPED_CLOUD_EVENT_ENVELOPE = {
    "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
    "message": {
        "data": base64.b64encode(to_queue_message(CLOUD_EVENT)),
        "messageId": "10",
        "attributes": {},
    },
    "id": 1,
}


@pytest.mark.parametrize(
    "test_name,queue_message,wrapped,expected,ret_type",
    [
        ("invalid", {}, True, None, type(None)),
        (
            "valid-wrapped",
            WRAPPED_CLOUD_EVENT_ENVELOPE,
            True,
            CLOUD_EVENT,
            SimpleCloudEvent,
        ),
        (
            "valid-unwrapped",
            to_structured(CLOUD_EVENT),
            False,
            CLOUD_EVENT,
            SimpleCloudEvent,
        ),
    ],
)
def test_get_simple_cloud_event(
    mocker, test_name, queue_message, wrapped, expected, ret_type
):
    """Test that getting a simple cloud event works as expected."""
    app = flask.Flask(__name__)
    with app.app_context():
        with app.test_request_context(content_type="application/json") as session:
            ce = to_structured(CLOUD_EVENT)

            def mock_get_json():
                return queue_message

            mocker.patch.object(session.request, "get_json", mock_get_json)

            ce = GcpQueue.get_simple_cloud_event(session.request, wrapped=wrapped)

            assert isinstance(ce, ret_type)
            # The CE stamps the time it was created if none given, remove that
            with suppress(Exception):
                ce.time = None
            assert ce == expected
