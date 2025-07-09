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

# import dpath.util
import pytest

from business_pay.services.queue import QueueService


def test_nats_stan_config(app):
    """Assert that all of the NATS & STAN configuration is set."""
    assert app.config.get("NATS_SERVERS")
    assert app.config.get("NATS_CLIENT_NAME")
    assert app.config.get("NATS_CLUSTER_ID")
    assert app.config.get("NATS_FILER_SUBJECT")
    assert app.config.get("NATS_QUEUE")


@pytest.mark.asyncio
async def test_queue_connect_to_nats(app, stan_server):
    """Assert that the service can connect to the STAN Queue."""
    with app.app_context():
        queue = QueueService(app)

        # sanity check
        assert not queue.is_connected

        # test
        await queue.connect()
        assert queue.is_connected

        await queue.connect()
        assert queue.is_connected

        await queue.close()
        assert queue.is_closed


@pytest.mark.asyncio
async def test_queue_flask_teardown(app):
    """Assert that the service can connect to the STAN Queue."""
    queue = QueueService(app)
    queue.teardown(exception=None)
    assert queue.is_closed


@pytest.mark.asyncio
async def test_error_callback(caplog):
    """Assert the on_error callback logs a warning."""
    error_msg = "test error"
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_error(e=Exception(error_msg))

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_disconnect_callback(caplog):
    """Assert the on_disconnect callback logs a warning."""
    error_msg = "Disconnected from NATS"
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_disconnect()

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_close_callback(caplog):
    """Assert the on_close callback logs a warning."""
    error_msg = "Closed connection to NATS"
    with caplog.at_level(logging.WARNING):
        queue = QueueService()
        await queue.on_close()

        assert error_msg in caplog.text


@pytest.mark.asyncio
async def test_on_reconnect_callback(caplog, app, stan_server):
    """Assert the reconnect callback logs a warning."""
    error_msg = "Reconnected to NATS"
    with caplog.at_level(logging.WARNING):
        queue = QueueService(app)
        await queue.connect()
        await queue.on_reconnect()

        assert error_msg in caplog.text
        # assert queue.nats.connected_url.netloc in caplog.text
        await queue.close()
