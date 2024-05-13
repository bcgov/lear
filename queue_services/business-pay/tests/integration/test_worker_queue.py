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
"""Test Suite to ensure the worker routines are working as expected."""
import asyncio
import base64
# import datetime
import random
from datetime import datetime
from datetime import timezone
from http import HTTPStatus

import pytest
# from entity_queue_common.messages import get_data_from_msg, get_filing_id_from_msg
# from entity_queue_common.service_utils import subscribe_to_queue
from .utils import subscribe_to_queue
from simple_cloudevent import SimpleCloudEvent, to_queue_message

# from .utils import helper_add_payment_to_queue
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
        res = client.post('/')
        assert res.status_code == 200

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
async def test_no_message(app, session, client, client_id, future, stan_server): #, event_loop):
    """Return a 4xx when an no JSON present."""

    ##-# using test_client()
    def sync_test():
        # with app.test_client() as client:
        rv = client.post('/')
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
    filing_type = 'annualReport'
    payment_token = random.SystemRandom().getrandbits(0x58)

    mocker.patch('google.oauth2.id_token.verify_oauth2_token',
                   return_value={'claim': 'succcess'})

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
            nats_queue.stan_connection_options ={'client_id': client_id}
            nats_queue.cb_handler = cb_file_handler
            nats_queue.subscription_options ={
                'subject': 'filer',
                'queue': 'filer',
                'durable_name': 'filer',
            }

            with app.test_client() as client:

                # SETUP ######################

                create_filing(session, filing_id, filing_type, payment_token)
                ce = create_test_payment_cloud_event(pay_token=payment_token,
                                                    pay_status= 'COMPLETED',
                                                    filing_id=filing_id,
                )
                envelope = create_test_envelope(ce)
                headers=dict(Authorization=f"Bearer doesn't matter",)
                 
                rv = client.post('/', json=envelope, headers=headers)

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
            found_filing = True
        elif msg.data == b'{"email": {"filingId": 12, "type": "annualReport"}}':
            found_email_msg = True
            
    assert found_filing
    assert found_email_msg




def create_test_payment_cloud_event(pay_token:str,
                                    pay_status:str = 'COMPLETED',
                                    filing_id: int = None,
                                    ):
    ce = SimpleCloudEvent(
    id="fake-id",
    source="fake-for-tests",
    subject="fake-subject",
    type="payment",
    data={
        "paymentToken": {
            "id": pay_token,
            "statusCode": pay_status,
            "filingIdentifier": filing_id,
            "corpTypeCode": "BC",
        }
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
