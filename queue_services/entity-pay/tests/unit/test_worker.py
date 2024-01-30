# Copyright © 2023 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the 'License');
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
"""The Test Suites to ensure that the worker is operating correctly."""
import base64
import random
from http import HTTPStatus

import pytest
from legal_api.models import Filing
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from entity_pay.resources.worker import get_filing_by_payment_id, get_payment_token
from tests.unit import create_filing, create_legal_entity, nested_session


def test_no_message(client):
    """Return a 4xx when an no JSON present."""

    rv = client.post("/")

    assert rv.status_code == HTTPStatus.OK


CLOUD_EVENT = SimpleCloudEvent(
    id="fake-id",
    source="fake-for-tests",
    subject="fake-subject",
    type="payment",
    data={
        "paymentToken": {
            "id": "29590",
            "statusCode": "COMPLETED",
            "filingIdentifier": 12345,
            "corpTypeCode": "BC",
        }
    },
)
#
# This needs to mimic the envelope created by GCP PubSb when call a resource
#
CLOUD_EVENT_ENVELOPE = {
    "subscription": "projects/PUBSUB_PROJECT_ID/subscriptions/SUBSCRIPTION_ID",
    "message": {
        "data": base64.b64encode(to_queue_message(CLOUD_EVENT)).decode("UTF-8"),
        "messageId": "10",
        "attributes": {},
    },
    "id": 1,
}


@pytest.mark.parametrize(
    "test_name,queue_envelope,expected",
    [("invalid", {}, HTTPStatus.OK), ("valid", CLOUD_EVENT_ENVELOPE, HTTPStatus.OK)],
)
def test_simple_cloud_event(client, session, test_name, queue_envelope, expected):
    with nested_session(session):
        filing = Filing()
        filing.payment_token = 29590
        filing.save()

        rv = client.post("/", json=CLOUD_EVENT_ENVELOPE)

        assert rv.status_code == expected


def test_get_payment_token():
    """Test that the payment token is retrieved."""
    from copy import deepcopy

    CLOUD_EVENT_TEMPLATE = {
        "data": {
            "paymentToken": {
                "id": 29590,
                "statusCode": "COMPLETED",
                "filingIdentifier": None,
                "corpTypeCode": "BC",
            }
        },
        "id": 29590,
        "source": "sbc-pay",
        "subject": "BC1234567",
        "time": "2023-07-05T22:04:25.952027",
        "type": "payment",
    }

    # base - should pass
    ce_dict = deepcopy(CLOUD_EVENT_TEMPLATE)
    ce = SimpleCloudEvent(**ce_dict)
    payment_token = get_payment_token(ce)
    assert payment_token
    assert payment_token.id == ce_dict["data"]["paymentToken"]["id"]

    # wrong type
    ce_dict = deepcopy(CLOUD_EVENT_TEMPLATE)
    ce_dict["type"] = "not-a-payment"
    ce = SimpleCloudEvent(**ce_dict)
    payment_token = get_payment_token(ce)
    assert not payment_token


def test_process_payment_failed(app, session, client, mocker):
    """Assert that an AR filling status is set to error if payment transaction failed."""
    from legal_api.models import Filing, LegalEntity

    from entity_pay.resources.worker import get_filing_by_payment_id
    from entity_pay.services import queue

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = "CP1234567"

    # setup
    business = create_legal_entity(identifier)
    business_id = business.id
    filing = create_filing(payment_id, None, business.id)
    payment_token = {
        "paymentToken": {
            "id": payment_id,
            "statusCode": "TRANSACTION_FAILED",
            "filingIdentifier": filing.id,
            "corpTypeCode": "BC",
        }
    }

    message = helper_create_cloud_event_envelope(source="sbc-pay", subject="payment", data=payment_token)

    def mock_publish():
        return {}

    mocker.patch.object(queue, "publish", mock_publish)

    # TEST
    # await process_payment(payment_token, app)
    rv = client.post("/", json=message)

    # Check
    assert rv.status_code == HTTPStatus.OK

    # Get modified data
    filing_from_db = get_filing_by_payment_id(int(payment_id))

    # check it out
    assert filing_from_db.business_id == business_id
    assert filing_from_db.status == Filing.Status.PENDING.value


def test_process_payment(app, session, client, mocker):
    """Assert that an AR filling status is set to error if payment transaction failed."""
    from legal_api.models import Filing

    from entity_pay.resources.worker import get_filing_by_payment_id
    from entity_pay.services import queue

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = "CP1234567"

    # setup
    legal_entity = create_legal_entity(identifier)
    legal_entity_id = legal_entity.id
    filing = create_filing(payment_id, None, legal_entity.id)
    payment_token = {
        "paymentToken": {
            "id": payment_id,
            "statusCode": "COMPLETED",
            "filingIdentifier": filing.id,
            "corpTypeCode": "BC",
        }
    }

    message = helper_create_cloud_event_envelope(source="sbc-pay", subject="payment", data=payment_token)
    # keep track of topics called on the mock
    topics = []

    def mock_publish(topic: str, payload: bytes):
        nonlocal topics
        topics.append(topic)
        return {}

    mocker.patch.object(queue, "publish", mock_publish)

    # TEST
    # await process_payment(payment_token, app)
    rv = client.post("/", json=message)

    # Check
    assert rv.status_code == HTTPStatus.OK
    assert len(topics) == 2
    assert "mailer" in topics
    assert "filer" in topics

    # Get modified data
    filing_from_db = get_filing_by_payment_id(int(payment_id))
    # check it out
    assert filing_from_db.business_id == legal_entity_id
    assert filing_from_db.status == Filing.Status.PAID.value


def helper_create_cloud_event_envelope(
    cloud_event_id: str = None,
    source: str = "fake-for-tests",
    subject: str = "fake-subject",
    type: str = "payment",
    data: dict = {},
    pubsub_project_id: str = "PUBSUB_PROJECT_ID",
    subscription_id: str = "SUBSCRIPTION_ID",
    message_id: int = 1,
    envelope_id: int = 1,
    attributes: dict = {},
    ce: SimpleCloudEvent = None,
):
    if not data:
        data = {
            "paymentToken": {
                "id": "29590",
                "statusCode": "COMPLETED",
                "filingIdentifier": 12345,
                "corpTypeCode": "BC",
            }
        }
    if not ce:
        ce = SimpleCloudEvent(id=cloud_event_id, source=source, subject=subject, type=type, data=data)
    #
    # This needs to mimic the envelope created by GCP PubSb when call a resource
    #
    envelope = {
        "subscription": f"projects/{pubsub_project_id}/subscriptions/{subscription_id}",
        "message": {
            "data": base64.b64encode(to_queue_message(ce)).decode("UTF-8"),
            "messageId": str(message_id),
            "attributes": attributes,
        },
        "id": envelope_id,
    }
    return envelope
