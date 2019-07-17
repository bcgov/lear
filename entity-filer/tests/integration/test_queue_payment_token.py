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
"""The Test Suites to ensure we can retrieve and decode payment tokens from the Queue."""
import asyncio
import json

import dpath.util
import pytest

from .utils import subscribe_to_queue


@pytest.mark.asyncio
async def test_get_queued_payment_tokens(app, stan_server, event_loop, client_id, entity_stan, future):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # Call back for the subscription
    msgs = []

    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 10:
            future.set_result(True)

    entity_subject = await subscribe_to_queue(entity_stan, cb)

    # add payment tokens to queue
    for i in range(0, 5):
        payload = {'paymentToken': {'id': 1234 + i, 'statusCode': 'COMPLETED'}}
        await entity_stan.publish(subject=entity_subject,
                                  payload=json.dumps(payload).encode('utf-8'))
    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:
        print(err)

    # check the payment tokens were retrieved from the queue
    assert len(msgs) == 5
    for i in range(0, 5):
        m = msgs[i]
        assert 'paymentToken' in m.data.decode('utf-8')
        assert 'COMPLETED' == dpath.util.get(json.loads(m.data.decode('utf-8')),
                                             'paymentToken/statusCode')
        assert m.sequence == i + 1
