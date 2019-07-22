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
import functools
import os
import random
import signal


from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN

from entity_filer.service_utils import closed_cb, error_cb, logger, signal_handler  # noqa I001; sort issue due to comments on the NATS & STAN lines
from entity_filer.worker import cb_subscription_handler  # noqa I001; sort issue due to comments on the NATS & STAN lines


async def run(loop):  # pylint: disable=too-many-locals
    """Run the main application loop for the service.

    This runs the main top level service functions for working with the Queue.
    """
    # NATS client connections
    nc = NATS()
    sc = STAN()

    async def reconnected_cb():
        """Connect to the NATS services.

        This gets called when the client successfully connects, or reconnects.
        """
        logger.info('Connected to NATS at %s...', nc.connected_url.netloc)

    async def close():
        """Close the stream and nats connections."""
        await sc.close()
        await nc.close()

    # Connection and Queue configuration.
    def nats_connection_options():
        return {
            'servers': os.getenv('NATS_SERVERS', 'nats://127.0.0.1:4222').split(','),
            'io_loop': loop,
            'error_cb': error_cb,
            'closed_cb': closed_cb,
            'reconnected_cb': reconnected_cb,
            'name': os.getenv('NATS_CLIENT_NAME', 'entity.filing.worker')
        }

    def stan_connection_options():
        return {
            'cluster_id': os.getenv('NATS_CLUSTER_ID', 'test-cluster'),
            'client_id': str(random.SystemRandom().getrandbits(0x58)),
            'nats': nc
        }

    def subscription_options():
        return {
            'subject': os.getenv('NATS_SUBJECT', 'entity.filings'),
            'queue': os.getenv('NATS_QUEUE', 'filing-worker'),
            'durable_name': os.getenv('NATS_QUEUE', 'filing-worker') + '_durable',
            'cb': cb_subscription_handler
        }

    try:
        # Connect to the NATS server, and then use that for the streaming connection.
        await nc.connect(**nats_connection_options())
        await sc.connect(**stan_connection_options())

        # Attach the callback queue
        await sc.subscribe(**subscription_options())
        logger.info('Subscribe the callback: %s to the queue: %s.',
                    subscription_options().get('cb').__name__, subscription_options().get('queue'))

        # register the signal handler
        for sig in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, sig),
                                    functools.partial(signal_handler, sig_loop=loop, sig_nc=nc, task=close)
                                    )

    except Exception as e:  # pylint: disable=broad-except
        # TODO tighten this error and decide when to bail on the infinite reconnect
        logger.error(e)


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(event_loop))
    try:
        event_loop.run_forever()
    finally:
        event_loop.close()
