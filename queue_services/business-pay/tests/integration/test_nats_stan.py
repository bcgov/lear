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
    
    file_handler_subject = 'main'
    subject = f'entity_queue.{file_handler_subject}'
    queue_name = f'entity_durable_name.{file_handler_subject}'
    durable_name = queue_name

    await sc.subscribe(subject=subject,
                       queue=queue_name,
                       durable_name=durable_name,
                       cb=cb_file_handler)

    identifier = 12345
    queue_message = create_filing_msg(identifier)
    await sc.publish(subject=subject,
                     payload=json.dumps(queue_message).encode('utf-8'))

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
async def test_fixture_entity_stan(entity_stan, stan_server, future, event_loop, client_id):
    """Basic test to ensure the fixtures, loops and Python version are correct."""

    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)
    
    file_handler_subject = 'main'
    subject = f'entity_queue.{file_handler_subject}'
    queue_name = f'entity_durable_name.{file_handler_subject}'
    durable_name = queue_name

    # entity_stan = await get_stan(event_loop, client_id)
    sc = entity_stan[1]

    await sc.subscribe(subject=subject,
                       queue=queue_name,
                       durable_name=durable_name,
                       cb=cb_file_handler)

    identifier = 12345
    queue_message = create_filing_msg(identifier)
    await sc.publish(subject=subject,
                     payload=json.dumps(queue_message).encode('utf-8'))

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # noqa: B902
        print(err)

    # check it out
    assert len(msgs) == 1
    assert str(identifier) in msgs[0].data.decode()


@pytest_asyncio.fixture(scope='function')
async def get_stan(event_loop, client_id):
    nc = NATS()
    # event_loop = asyncio.get_running_loop()
    await nc.connect(io_loop=event_loop)
    await nc.connect()

    sc = STAN()
    await sc.connect("test-cluster", client_id, nats=nc)

    return sc


# async def test_nats_queue(entity_stan, stan_server, future, event_loop, client_id):
@pytest.mark.asyncio
async def test_nats_queue(app, stan_server, future, event_loop, client_id):
    """Basic test to ensure the fixtures, loops and Python version are correct."""

    from business_pay.services import nats_queue
    from business_pay.config import Config
    # file handler callback
    msgs = []

    async def cb_file_handler(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 1:
            future.set_result(True)

    file_handler_subject = 'main'
    subject = f'entity_queue.{file_handler_subject}'
    queue_name = f'entity_durable_name.{file_handler_subject}'
    durable_name = queue_name

    nats_queue._loop = event_loop
    nats_queue.config = Config
    nats_queue.stan_connection_options ={'client_id': client_id}
    nats_queue.cb_handler = cb_file_handler
    nats_queue.subscription_options ={
        'subject': subject,
        'queue': queue_name,
        'durable_name': durable_name,
    }
    await nats_queue.connect()

    identifier = 12345
    queue_message = create_filing_msg(identifier)
    await nats_queue.publish(subject=subject,
                     msg=queue_message)

    try:
        await asyncio.wait_for(future, 2, loop=event_loop)
    except Exception as err:  # noqa: B902
        print(err)

    # check it out
    assert len(msgs) == 1
    assert str(identifier) in msgs[0].data.decode()
