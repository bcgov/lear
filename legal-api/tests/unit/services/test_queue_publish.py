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

"""Tests to assure the Queue Services.

Test-Suite to ensure that the Queue Publication Service is working as expected.
"""
import asyncio
import json
import logging

import dpath.util
import pytest

from legal_api.services.queue import QueueService
from tests import integration_nats


def test_nats_stan_config(app):
    """Assert that all of the NATS & STAN configuration is set."""
    assert app.config.get('NATS_SERVERS')
    assert app.config.get('NATS_CLIENT_NAME')
    assert app.config.get('NATS_CLUSTER_ID')
    assert app.config.get('NATS_COLIN_SUBJECT')
    assert app.config.get('NATS_QUEUE')


@pytest.mark.asyncio
async def test_queue_properties_with_no_flask_ctx():
    """Assert that the queue clients cannot be checked."""
    queue = QueueService()

    assert not queue.nats
    assert not queue.stan
    assert queue.is_closed
    assert not queue.is_connected

    await queue.connect()
    assert not queue.is_connected


@integration_nats
@pytest.mark.asyncio
async def test_queue_connect_to_nats(app_ctx, stan_server):
    """Assert that the service can connect to the STAN Queue."""
    queue = QueueService(app_ctx)

    # sanity check
    assert not queue.is_connected

    # test
    await queue.connect()
    assert queue.is_connected

    await queue.connect()
    assert queue.is_connected

    await queue.close()
    assert queue.is_closed


@integration_nats
# @pytest.mark.asyncio
async def test_queue_flask_teardown(app_ctx):
    """Assert that the service can connect to the STAN Queue."""
    queue = QueueService(app_ctx)
    queue.teardown(exception=None)
    assert queue.is_closed


@integration_nats
@pytest.mark.asyncio
async def test_async_publish_colin_filing(app_ctx, stan_server):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # SETUP
    msgs = []
    this_loop = asyncio.get_event_loop()
    future = asyncio.Future(loop=this_loop)
    queue = QueueService(app_ctx, this_loop)
    await queue.connect()

    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 5:
            future.set_result(True)

    await queue.stan.subscribe(subject=queue.subject,
                               queue='colin_queue',
                               durable_name='colin_queue',
                               cb=cb)

    # TEST - add some messages to the queue
    for i in range(0, 5):
        payload = {'colinFiling': {'id': 1234 + i, }}
        await queue.async_publish_json(payload=payload)
    try:
        await asyncio.wait_for(future, 2, loop=this_loop)
    except Exception as err:
        print(err)

    # await queue.close()

    # CHECK the colinFilings were retrieved from the queue
    assert len(msgs) == 5
    for i in range(0, 5):
        m = msgs[i]
        assert 'colinFiling' in m.data.decode('utf-8')
        assert 1234 + i == dpath.util.get(json.loads(m.data.decode('utf-8')),
                                          'colinFiling/id')


# @integration_nats
# @pytest.mark.asyncio
# async def test_publish_colin_filing(app_ctx, stan_server, event_loop):
#     """Assert that payment tokens can be retrieved and decoded from the Queue."""
#     # SETUP
#     msgs = []
#     # this_loop = asyncio.get_event_loop()
#     this_loop = event_loop
#     future = asyncio.Future(loop=this_loop)
#     queue = QueueService(app_ctx, this_loop)
#     await queue.connect()

#     async def cb(msg):
#         nonlocal msgs
#         nonlocal future
#         msgs.append(msg)
#         if len(msgs) == 5:
#             future.set_result(True)

#     await queue.stan.subscribe(subject=queue.subject,
#                                queue='colin_queue',
#                                durable_name='colin_queue',
#                                cb=cb)

#     # TEST - add some messages to the queue
#     for i in range(0, 5):
#         payload = {'colinFiling': {'id': 1234 + i, }}
#         queue.publish_json(payload=payload)
#     try:
#         await asyncio.wait_for(future, 2, loop=this_loop)
#     except Exception as err:
#         print(err)

#     # CHECK the colinFilings were retrieved from the queue
#     assert len(msgs) == 5
#     for i in range(0, 5):
#         m = msgs[i]
#         assert 'colinFiling' in m.data.decode('utf-8')
#         assert 1234 + i == dpath.util.get(json.loads(m.data.decode('utf-8')),
#                                           'colinFiling/id')


@pytest.mark.asyncio
async def test_error_callback(caplog):
    """Assert the on_error callback logs a warning."""
    error_msg = 'test error'
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_error(e=Exception(error_msg))

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_disconnect_callback(caplog):
    """Assert the on_disconnect callback logs a warning."""
    error_msg = 'Disconnected from NATS'
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_disconnect()

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_close_callback(caplog):
    """Assert the on_close callback logs a warning."""
    error_msg = 'Closed connection to NATS'
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_close()

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_reconnect_callback(caplog, app_ctx, stan_server):
    """Assert the reconnect callback logs a warning."""
    error_msg = 'Reconnected to NATS'
    with caplog.at_level(logging.WARNING):
        queue = QueueService(app_ctx)
        await queue.connect()
        await queue.on_reconnect()

        assert error_msg in caplog.text
        assert queue.nats.connected_url.netloc in caplog.text
        await queue.close()


@integration_nats
# @pytest.mark.asyncio
def test_publish_colin_filing_managed(app_ctx, stan_server):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    # SETUP
    msgs = []
    this_loop = asyncio.get_event_loop()
    # this_loop = event_loop
    future = asyncio.Future(loop=this_loop)
    queue = QueueService(app_ctx, this_loop)
    this_loop.run_until_complete(queue.connect())

    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 5:
            future.set_result(True)

    this_loop.run_until_complete(queue.stan.subscribe(subject=queue.subject,
                                                      queue='colin_queue',
                                                      durable_name='colin_queue',
                                                      cb=cb))

    # TEST - add some messages to the queue
    for i in range(0, 5):
        payload = {'colinFiling': {'id': 1234 + i, }}
        queue.publish_json(payload=payload)
    try:
        this_loop.run_until_complete(asyncio.wait_for(future, 2, loop=this_loop))
    except Exception as err:
        print(err)

    # CHECK the colinFilings were retrieved from the queue
    assert len(msgs) == 5
    for i in range(0, 5):
        m = msgs[i]
        assert 'colinFiling' in m.data.decode('utf-8')
        assert 1234 + i == dpath.util.get(json.loads(m.data.decode('utf-8')),
                                          'colinFiling/id')
