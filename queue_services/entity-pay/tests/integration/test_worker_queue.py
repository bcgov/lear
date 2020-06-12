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
import datetime
import random

import pytest
from entity_queue_common.messages import get_data_from_msg, get_filing_id_from_msg
from entity_queue_common.service_utils import subscribe_to_queue

from .utils import helper_add_payment_to_queue


@pytest.mark.asyncio
async def test_cb_subscription_handler(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker
    from entity_pay.worker import APP_CONFIG, cb_subscription_handler, get_filing_by_payment_id, qsm
    from legal_api.models import Business, Filing
    from tests.unit import create_filing, create_business

    # vars
    uuid = str(random.SystemRandom().getrandbits(0x58))
    payment_id = uuid
    identifier = 'CP1234567'
    # entity_subject = os.getenv('LEGAL_FILING_STAN_SUBJECT')
    # entity_queue = os.getenv('LEGAL_FILING_STAN_QUEUE')
    # entity_durable_name = os.getenv('LEGAL_FILING_STAN_DURABLE_NAME')
    entity_subject = f'test_subject.{uuid}'
    entity_queue = f'test_queue.{uuid}'
    entity_durable_name = f'test_durable.{uuid}'

    # setup
    business = create_business(identifier)
    business_id = business.id
    # create_filing(payment_id, AR_FILING, business.id)
    create_filing(payment_id, None, business.id)

    # register the handler to test it
    entity_subject = await subscribe_to_queue(entity_stan,
                                              entity_subject,
                                              entity_queue,
                                              entity_durable_name,
                                              cb_subscription_handler)

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = APP_CONFIG.FILER_PUBLISH_OPTIONS['subject']
    await subscribe_to_queue(entity_stan,
                             file_handler_subject,
                             f'entity_queue.{file_handler_subject}',
                             f'entity_durable_name.{file_handler_subject}',
                             cb_file_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # add payment tokens to queue
    await helper_add_payment_to_queue(entity_stan, entity_subject, payment_id=payment_id, status_code='COMPLETED')

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    # assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.PAID.value

    assert len(msgs) == 1
    assert get_filing_id_from_msg(msgs[0]) == filing.id


@pytest.mark.asyncio
async def test_publish_filing(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker
    from entity_pay.worker import APP_CONFIG, publish_filing, qsm
    from legal_api.models import Filing

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = APP_CONFIG.FILER_PUBLISH_OPTIONS['subject']
    await subscribe_to_queue(entity_stan,
                             file_handler_subject,
                             f'entity_queue.{file_handler_subject}',
                             f'entity_durable_name.{file_handler_subject}',
                             cb_file_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # Test
    filing = Filing()
    filing.id = 101
    await publish_filing(filing)

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check it out
    assert len(msgs) == 1
    assert get_filing_id_from_msg(msgs[0]) == filing.id


@pytest.mark.asyncio
async def test_publish_email_message(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker
    from entity_pay.worker import APP_CONFIG, publish_email_message, qsm
    from legal_api.models import Filing

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject']
    await subscribe_to_queue(entity_stan,
                             file_handler_subject,
                             f'entity_queue.{file_handler_subject}',
                             f'entity_durable_name.{file_handler_subject}',
                             cb_file_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # Test
    filing = Filing()
    filing.id = 101
    filing.filing_type = 'incorporationApplication'
    filing_date = datetime.datetime.utcnow()
    filing.filing_date = filing_date
    filing.effective_date = filing_date

    await publish_email_message(filing)

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check it out
    assert len(msgs) == 1
    assert get_data_from_msg(msgs[0], 'id') == filing.id
    assert get_data_from_msg(msgs[0], 'type') == filing.filing_type
    assert get_data_from_msg(msgs[0], 'option') == 'filed'
