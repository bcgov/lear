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
"""The Test Suite to ensure Queue messaging is working correctly."""
import asyncio

import pytest
from stan.aio.client import Subscription


@pytest.mark.asyncio
async def test_publish_acks(stan_server, event_loop, client_id, stan, future):
    """Assert that basic publishing toThe queue is working by just ensuring an ACK is received."""
    test_ack = None

    async def cb(ack):
        nonlocal test_ack
        nonlocal future
        test_ack = ack
        future.set_result(True)

    await stan.publish(subject='ack-check',
                       payload=b'test ack',
                       ack_handler=cb)

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # pylint: disable=broad-except; who cares, the test picks up the assert!
        print(err)

    assert test_ack


@pytest.mark.asyncio
async def test_durable_queue_request(stan_server, event_loop, client_id, stan, future):
    """Assert that we can publish subscribe to a durable queue."""
    msgs = []

    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 10:
            future.set_result(True)

    sub = await stan.subscribe(subject='test-durable-queue',
                               queue='test_durable',
                               durable_name='test_durable',
                               cb=cb)

    assert isinstance(sub, Subscription)

    for i in range(0, 10):
        await stan.publish(subject='test-durable-queue',
                           payload=b'test message')
    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)
    assert len(msgs) == 10
    for i in range(0, 10):
        m = msgs[i]
        assert m.sequence == i + 1
