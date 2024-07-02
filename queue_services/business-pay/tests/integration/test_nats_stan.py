# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
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
"""Test suite of the NATS setup."""
import asyncio
import json

import pytest
import pytest_asyncio
from nats.aio.client import Client as NATS
from stan.aio.client import Client as STAN
from stan.aio.errors import *

from business_pay.services import create_filing_msg


@pytest.mark.asyncio
async def test_connect(stan_server, future, event_loop, client_id):
    """Basic test to ensure the fixtures, loops and Python version are correct."""
    nc = NATS()
    # # event_loop = asyncio.get_running_loop()
    await nc.connect(io_loop=event_loop)
    # await nc.connect()

    sc = STAN()
    # await sc.connect("test-cluster", "client-123", nats=nc)
    await sc.connect("test-cluster", client_id, nats=nc)

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = "main"
    subject = f"entity_queue.{file_handler_subject}"
    queue_name = f"entity_durable_name.{file_handler_subject}"
    durable_name = queue_name

    await sc.subscribe(
        subject=subject, queue=queue_name, durable_name=durable_name, cb=cb_file_handler
    )

    identifier = 12345
    queue_message = create_filing_msg(identifier)
    await sc.publish(subject=subject, payload=json.dumps(queue_message).encode("utf-8"))

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # noqa: B902
        print(err)

    await sc.close()
    await nc.close()

    # check it out
    assert len(msgs) == 1
    assert str(identifier) in msgs[0].data.decode()


@pytest.mark.asyncio
async def test_fixture_entity_stan(
    entity_stan, stan_server, future, event_loop, client_id
):
    """Basic test to ensure the fixtures, loops and Python version are correct."""

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = "main"
    subject = f"entity_queue.{file_handler_subject}"
    queue_name = f"entity_durable_name.{file_handler_subject}"
    durable_name = queue_name

    # entity_stan = await get_stan(event_loop, client_id)
    sc = entity_stan[1]

    await sc.subscribe(
        subject=subject, queue=queue_name, durable_name=durable_name, cb=cb_file_handler
    )

    identifier = 12345
    queue_message = create_filing_msg(identifier)
    await sc.publish(subject=subject, payload=json.dumps(queue_message).encode("utf-8"))

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # noqa: B902
        print(err)

    # check it out
    assert len(msgs) == 1
    assert str(identifier) in msgs[0].data.decode()


@pytest_asyncio.fixture(scope="function")
async def get_stan(event_loop, client_id):
    nc = NATS()
    # event_loop = asyncio.get_running_loop()
    await nc.connect(io_loop=event_loop)
    await nc.connect()

    sc = STAN()
    await sc.connect("test-cluster", client_id, nats=nc)

    return sc
