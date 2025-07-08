# Copyright © 2024 Province of British Columbia
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
"""Test Suite to ensure the worker routines are working as expected."""
import asyncio
import base64
import random
from datetime import datetime
from datetime import timezone
from http import HTTPStatus

import pytest
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from business_pay.database import Filing


def create_filing(session, filing_id, filing_type, payment_token):
    from sqlalchemy import text

    sql = f"""
    INSERT into filings (id, effective_date,
    status, filing_type, payment_status_code,
    payment_id, payment_completion_date, source)
    VALUES (
    {filing_id}, '{datetime.now(timezone.utc)}',
    'PENDING', '{filing_type}', 'PENDING',
    '{payment_token}', null, 'test runner');
    """
    try:
        session.execute(text(sql))
    except Exception as err:
        print(err)
        raise err


@pytest.mark.asyncio
async def test_not_message(app, client):
    # ... same code as before

    ##-# using test_client()
    def sync_test():
        # with app.test_client() as client:
        res = client.post("/")
        assert res.status_code == 200

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
async def test_no_message(
    app, session, client, client_id, future, stan_server
):  # , event_loop):
    """Return a 4xx when an no JSON present."""

    ##-# using test_client()
    def sync_test():
        # with app.test_client() as client:
        rv = client.post("/")
        assert rv.status_code == HTTPStatus.OK

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


def create_test_payment_cloud_event(
    pay_token: str,
    pay_status: str = "COMPLETED",
    filing_id: int = None,
):
    ce = SimpleCloudEvent(
        id="fake-id",
        source="fake-for-tests",
        subject="fake-subject",
        type="bc.registry.payment",
        data={
            "id": pay_token,
            "statusCode": pay_status,
            "filingIdentifier": filing_id,
            "corpTypeCode": "BC",
        },
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


def test_complete_worker(app, session, stan_server, mocker):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # SETUP
    # lots of setup ...
    from business_pay.services import queue

    msgs = []
    messages_expected = 2  # 1 - filer & 1 - email == 2 messages

    # Override the app.config for the NATS/STAN configuration
    test_subject_name = "test-subject"
    app.config["NATS_QUEUE"] = test_subject_name
    app.config["NATS_FILER_SUBJECT"] = test_subject_name
    app.config["NATS_EMAILER_SUBJECT"] = test_subject_name
    app.config["FILER_PUBLISH_OPTIONS"] = {"subject": test_subject_name}
    app.config["EMAIL_PUBLISH_OPTIONS"] = {"subject": test_subject_name}

    # setup loop
    this_loop = asyncio.get_event_loop()
    future = asyncio.Future(loop=this_loop)
    queue.init_app(app, loop=this_loop)
    this_loop.run_until_complete(queue.connect())

    # Define the Callback to get the posted Queue messages
    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == messages_expected:
            future.set_result(True)

    # Subscribe to the Queue
    queue_name = app.config.get("NATS_QUEUE")
    this_loop.run_until_complete(
        queue.stan.subscribe(
            subject=test_subject_name,
            queue=queue_name,
            durable_name=test_subject_name,
            cb=cb,
        )
    )

    filing_id = 12
    filing_type = "annualReport"
    payment_token = random.SystemRandom().getrandbits(0x58)

    # Mock the JWT callback for GCP
    claim = {
        "email_verified": app.config.get("SUB_SERVICE_ACCOUNT"),
        "email": app.config.get("SUB_SERVICE_ACCOUNT"),
    }
    mocker.patch("google.oauth2.id_token.verify_oauth2_token", return_value=claim)

    #
    # TEST - Call the Flask endpoint with a GCP type message
    #
    with app.test_client() as client:
        create_filing(session, filing_id, filing_type, payment_token)
        ce = create_test_payment_cloud_event(
            pay_token=payment_token,
            pay_status="COMPLETED",
            filing_id=filing_id,
        )
        envelope = create_test_envelope(ce)
        headers = {
            "Authorization": f"Bearer doesn't matter",
            "Content-Type": "application/json",
        }

        rv = client.post("/", json=envelope, headers=headers)

        # CHECK the call completed
        assert rv.status_code == HTTPStatus.OK

    # Get the messages from the Queue, 2s timeout
    try:
        this_loop.run_until_complete(asyncio.wait_for(future, 2, loop=this_loop))
    except Exception as err:
        print(err)
        raise err

    # CHECK the NATS message were retrieved from the queue
    assert len(msgs) == messages_expected
    for msg in msgs:
        if msg.data == b'{"filing": {"id": 12}}':
            found_filing_msg = True
        elif (
            msg.data
            == b'{"email": {"filingId": 12, "type": "annualReport", "option": "PAID"}}'
        ):
            found_email_msg = True

    assert found_filing_msg
    assert found_email_msg
