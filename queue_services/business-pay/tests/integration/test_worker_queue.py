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


@pytest.mark.asyncio
async def test_full_worker_process(app, session, client_id, stan_server, mocker):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    # from entity_queue_common.service import ServiceWorker
    # from legal_api.models import Filing
    from business_pay.database import Filing
    from business_pay import Config
    from business_pay.services import nats_queue

    msgs = []
    future = None
    filing_id = 12
    filing_type = "annualReport"
    payment_token = random.SystemRandom().getrandbits(0x58)

    claim = {
        "email_verified": app.config.get("SUB_SERVICE_ACCOUNT"),
        "email": app.config.get("SUB_SERVICE_ACCOUNT"),
    }
    mocker.patch("google.oauth2.id_token.verify_oauth2_token", return_value=claim)

    ##-# using test_client()
    def sync_test(loop):
        nonlocal future

        # loop = asyncio.get_running_loop()
        print(loop)
        future = asyncio.Future(loop=loop)
        with app.app_context():
            # file handler callback
            async def cb_file_handler(msg):
                nonlocal msgs
                nonlocal future
                msgs.append(msg)
                if len(msgs) == 1:
                    future.set_result(True)

            nats_queue._loop = loop
            nats_queue.name = datetime.now().isoformat()
            nats_queue.config = Config
            nats_queue.stan_connection_options = {"client_id": client_id}
            nats_queue.cb_handler = cb_file_handler
            nats_queue.subscription_options = {
                "subject": "filer",
                "queue": "filer",
                "durable_name": "filer",
            }

            with app.test_client() as client:

                # SETUP ######################

                create_filing(session, filing_id, filing_type, payment_token)
                ce = create_test_payment_cloud_event(
                    pay_token=payment_token,
                    pay_status="COMPLETED",
                    filing_id=filing_id,
                )
                envelope = create_test_envelope(ce)
                headers = dict(
                    Authorization=f"Bearer doesn't matter",
                )

                rv = client.post("/", json=envelope, headers=headers)

                assert rv.status_code == HTTPStatus.OK

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test, loop)

    try:
        await asyncio.wait_for(future, 2, loop=loop)
    except Exception as err:  # noqa: B902
        print(err)

    assert len(msgs) == 2
    found_filing_msg = False
    found_email_msg = False
    for msg in msgs:
        if msg.data == b'{"filing": {"id": 12}}':
            found_filing_msg = True
        elif msg.data == b'{"email": {"filingId": 12, "type": "annualReport"}}':
            found_email_msg = True

    assert found_filing_msg
    assert found_email_msg


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
