# """Service for listening and handling Queue Messages.

# This service registers interest in listening to a Queue and processing received messages.
# """
import asyncio
import functools
import json
import signal
from typing import Dict

from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN
from flask import Flask
from structured_logging import StructuredLogging
logger = StructuredLogging.get_logger()

class NatsQueue:
    def __init__(self, *,
                 app: Flask = None,
                 loop=None,
                 cb_handler=None,
                 nats_connection_options=None,
                 stan_connection_options=None,
                 subscription_options=None,
                 nats_connection=None,
                 stan_connection=None,
                 config=None,
                 name=None,
    ):
        self.sc = stan_connection
        self.nc = nats_connection
        self._start_seq = 0
        self._loop = loop
        self.cb_handler = cb_handler
        self.nats_connection_options = nats_connection_options or {}
        self.stan_connection_options = stan_connection_options or {}
        self.subscription_options = subscription_options or {}
        self.config = config
        self._name = name
        if app:
            self.init_app(app=app,
                        loop=loop,
                        cb_handler=cb_handler,
                        nats_connection_options=nats_connection_options,
                        stan_connection_options=stan_connection_options,
                        subscription_options=subscription_options,
                        nats_connection=nats_connection,
                        stan_connection=stan_connection,
                        config=config,
                        name=name,
                        )

    def init_app(self,
                 app: Flask = None,
                 loop=None,
                 cb_handler=None,
                 nats_connection_options=None,
                 stan_connection_options=None,
                 subscription_options=None,
                 nats_connection=None,
                 stan_connection=None,
                 config=None,
                 name=None,
    ):
        self.app = app
        self.sc = stan_connection
        self.nc = nats_connection
        self._start_seq = 0
        self._loop = loop
        self.cb_handler = cb_handler
        self.nats_connection_options = nats_connection_options or {}
        self.stan_connection_options = stan_connection_options or {}
        self.subscription_options = subscription_options or {}
        self.config = config
        self._name = name

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

    @property
    def name(self):
        """Return worker name of this service."""
        return self._name

    @name.setter
    def name(self, value):
        """Set worker name of this service."""
        self._name = value

    async def connect(self):
        """Connect the service worker to the NATS/STAN Queue.

        Also handles reconnecting when the network has dropped the connection.
        Both the NATS and the STAN clients need to be reinstantiated to work correctly.

        """
        try:
            if await self.is_healthy:
                return
        except Exception as err:
            print(err)
        
        if not self.config:
            logger.error('missing configuration object.')
            raise AttributeError('missing configuration object.')

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
            ** {
                # 'loop': self._loop,
                'error_cb': error_cb
                },
            **self.nats_connection_options
        }

        stan_connection_options = {
            **self.config.STAN_CONNECTION_OPTIONS,
            **{'nats': self.nc,
               'conn_lost_cb': self._stan_conn_lost_cb,
            #    'loop': self._loop,
               },
            **self.stan_connection_options
        }

        subscription_options = {
            **self.config.SUBSCRIPTION_OPTIONS,
            **{'cb': self.cb_handler},
            **self.subscription_options
        }
        try:
            await self.nc.connect(**nats_connection_options)
            await self.sc.connect(**stan_connection_options)
            await self.sc.subscribe(**subscription_options)
        except Exception as err:
            print(err)

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

    async def publish(self, subject: str, msg: Dict):
        """Publish the msg as a JSON struct to the subject, using the streaming NATS connection."""
        await self.sc.publish(subject=subject,
                              payload=json.dumps(msg).encode('utf-8'))

async def error_cb(e):
    """Emit error message to the log stream."""
    logger.error('NATS library emitted an error. %s', e, stack_info=True)
