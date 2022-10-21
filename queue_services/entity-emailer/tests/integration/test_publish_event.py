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
"""Test Suite to ensure event publishing is working as expected."""
import asyncio
import json

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(scope='session')
@pytest.mark.asyncio
async def test_publish_event(app, session, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that email event is placed on the queue."""
    # Call back for the subscription
    from entity_queue_common.service import ServiceWorker

    from entity_emailer.worker import APP_CONFIG, publish_event, qsm

    # email handler callback
    msgs = []

    async def cb_email_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    event_handler_subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']

    await entity_stan.subscribe(subject=event_handler_subject,
                                queue=f'entity_queue.{event_handler_subject}',
                                durable_name=f'entity_durable_name.{event_handler_subject}',
                                cb=cb_email_handler)

    s = ServiceWorker()
    s.sc = entity_stan
    qsm.service = s

    # Setup

    # Test
    await publish_event({'email': {'type': 'bn'}})

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # noqa B902
        print(err)

    # check it out
    assert len(msgs) == 1

    event_msg = json.loads(msgs[0].data.decode('utf-8'))
    assert event_msg['email']['type'] == 'bn'
