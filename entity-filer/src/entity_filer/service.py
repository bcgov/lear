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
import signal


from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN

from entity_filer.config import get_named_config  # noqa I001; sort issue due to comments on the NATS & STAN lines
from entity_filer.probes import Probes  # noqa I001; sort issue due to comments on the NATS & STAN lines
from entity_filer.service_utils import error_cb, logger, signal_handler  # noqa I001; sort issue due to comments on the NATS & STAN lines
from entity_filer.worker import cb_subscription_handler  # noqa I001; sort issue due to comments on the NATS & STAN lines


class ServiceWorker():
    """Wrap a service that will listen to the Queue Stream."""

    def __init__(self, *,
                 loop=None,
                 cb_handler=None,
                 nats_connection_options=None,
                 stan_connection_options=None,
                 subscription_options=None,
                 config=get_named_config()
                 ):
        """Initialize the service to a working state."""
        self.sc = None
        self.nc = None
        self._start_seq = 0
        self._loop = loop
        self.cb_handler = cb_handler
        self.nats_connection_options = nats_connection_options or {}
        self.stan_connection_options = stan_connection_options or {}
        self.subscription_options = subscription_options or {}
        self.config = config

        async def conn_lost_cb(error):
            logger.info('Connection lost:%s', error)
            for i in range(0, 100):
                try:
                    logger.info('Reconnecting, attempt=%i...', i)
                    await self.connect()
                except Exception as e:  # pylint: disable=broad-except; catch all errors from client framework
                    logger.error('Error %s', e.with_traceback(), stack_info=True)
                    continue
                break
        self._stan_conn_lost_cb = conn_lost_cb

    @property
    async def is_healthy(self):
        """Determine if the service is working."""
        if self.nc and self.nc.is_connected:
            return True
        return False

    @property
    async def is_ready(self):
        """Determine if the service is ready to perform."""
        if self.nc and self.nc.is_connected:
            return True
        return False

    async def connect(self):
        """Connect the service worker to th3e NATS/STAN Queue.

        Also handles reconnecting when the network has dropped the connection.
        Both the NATS and the STAN clients need to be reinstantiated to work correctly.

        """
        logger.info('Connecting...')
        if self.nc:
            try:
                logger.debug('close old NATS client')
                await self.nc.close()
            except asyncio.CancelledError as err:
                logger.debug('closing stale connection err:%s', err)
            finally:
                self.nc = None

        self.nc = NATS()
        self.sc = STAN()

        nats_connection_options = {
            **self.config.NATS_CONNECTION_OPTIONS,
            **{'loop': self._loop,
               'error_cb': error_cb},
            **self.nats_connection_options
        }

        stan_connection_options = {
            **self.config.STAN_CONNECTION_OPTIONS,
            **{'nats': self.nc,
               'conn_lost_cb': self._stan_conn_lost_cb,
               'loop': self._loop},
            **self.stan_connection_options
        }

        subscription_options = {
            **self.config.SUBSCRIPTION_OPTIONS,
            **{'cb': self.cb_handler},
            **self.subscription_options
        }

        await self.nc.connect(**nats_connection_options)
        await self.sc.connect(**stan_connection_options)
        await self.sc.subscribe(**subscription_options)

        logger.info('Subscribe the callback: %s to the queue: %s.',
                    subscription_options.get('cb').__name__ if subscription_options.get('cb') else 'no_call_back',
                    subscription_options.get('queue'))

    async def close(self):
        """Close the stream and nats connections."""
        try:
            await self.sc.close()
            await self.nc.close()
        except Exception as err:  # pylint: disable=broad-except; catch all errors to log out when closing the service.
            logger.debug('error when closing the streams: %s', err, stack_info=True)


async def run(loop):  # pylint: disable=too-many-locals
    """Run the main application loop for the service.

    This runs the main top level service functions for working with the Queue.
    """
    service = ServiceWorker(loop=loop, cb_handler=cb_subscription_handler)
    probe = Probes(components=[service], loop=loop)

    async def close():
        await service.close()
        my_loop = asyncio.get_running_loop()
        await asyncio.sleep(0.1, loop=my_loop)
        my_loop.stop()

    try:
        await probe.start()
        await service.connect()

        # register the signal handler
        for sig in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, sig),
                                    functools.partial(signal_handler, sig_loop=loop, task=close)
                                    )

    except Exception as e:  # pylint: disable=broad-except
        # TODO tighten this error and decide when to bail on the infinite reconnect
        logger.error(e)


if __name__ == '__main__':
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop))
        event_loop.run_forever()
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        logger.error('problem in running the service: %s', err, stack_info=True, exc_info=True)
    finally:
        event_loop.close()
