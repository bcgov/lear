# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Service for listening and handling Queue Messages.

This service registers interest in listening to a Queue and processing received messages.
"""
import asyncio
import logging
import signal


from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)d-%(name)s-%(levelname)s > %(module)s:%(filename)s:%(lineno)d-%(funcName)s:%(message)s',
    datefmt='%H:%M:%S',
)
logging.getLogger('asyncio').setLevel(logging.INFO)


async def run(loop):
    """Run the main application loop for the service.

    This runs the main top level service functions for working with the Queue.
    """
    logger = logging.getLogger('asyncio')

    nc = NATS()

    async def error_cb(e):
        logger.error(e)

    async def closed_cb():
        logger.info('Connection to NATS is closed.')
        await asyncio.sleep(0.1, loop=loop)
        loop.stop()

    async def reconnected_cb():
        logger.info('Connected to NATS at %s...', nc.connected_url.netloc)

    async def subscribe_handler(msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        logger.info('Received a message on %s, reply %s: %s', subject, reply, data)

    options = {
        'io_loop': loop,
        'error_cb': error_cb,
        'closed_cb': closed_cb,
        'reconnected_cb': reconnected_cb,
        'name': 'entity.filing.tester'
    }

    try:
        await nc.connect(**options)
    except Exception as e:  # pylint: disable=broad-except
        # TODO tighten this error and decide when to bail on the infinite reconnect
        logger.error(e)

    logger.info('Connected to NATS at %s...', nc.connected_url.netloc)

    def signal_handler():
        if nc.is_closed:
            return
        logger.info('Signal to Shutdown received, disconnecting ...')
        loop.create_task(nc.close())

    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), signal_handler)

    await nc.subscribe('entity.filings', 'filing-worker-queue', subscribe_handler)


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(event_loop))
    try:
        event_loop.run_forever()
    finally:
        event_loop.close()
