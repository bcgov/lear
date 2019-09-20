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

"""This provides the service to publish to the queue."""
import asyncio
import json
import logging
import random
import string

from flask import _app_ctx_stack
from nats.aio.client import Client as NATS, DEFAULT_CONNECT_TIMEOUT  # noqa N814; by convention the name is NATS
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN


class QueueService():
    """Provides services to use the Queue from Flask.

    For ease of use, this follows the style of a Flask Extension
    """

    def __init__(self, app=None, loop=None):
        """Initialize, supports setting the app context on instantiation."""
        # Default NATS Options
        self.name = 'default_api_client'
        self.nats_options = {}
        self.stan_options = {}
        self.loop = loop
        self.nats_servers = None
        self.subject = None

        self.logger = logging.getLogger()

        if app is not None:
            self.init_app(app, self.loop)

    def init_app(self, app, loop=None,
                 nats_options=None, stan_options=None):
        """Initialize the extension.

        :param app: Flask app
        :return: naked
        """
        self.name = app.config.get('NATS_CLIENT_NAME')
        self.loop = loop or asyncio.get_event_loop()
        self.nats_servers = app.config.get('NATS_SERVERS').split(',')
        self.subject = app.config.get('NATS_COLIN_SUBJECT')

        default_nats_options = {
            'name': self.name,
            'io_loop': self.loop,
            'servers': self.nats_servers,
            'connect_timeout': app.config.get('NATS_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT),

            # NATS handlers
            'error_cb': self.on_error,
            'closed_cb': self.on_close,
            'reconnected_cb': self.on_reconnect,
            'disconnected_cb': self.on_disconnect,
        }
        if not nats_options:
            nats_options = {}

        self.nats_options = {**default_nats_options, **nats_options}

        default_stan_options = {
            'cluster_id': app.config.get('NATS_CLUSTER_ID'),
            'client_id':
            (self.name.
             lower().
             strip(string.whitespace)
             ).translate({ord(c): '_' for c in string.punctuation})
            + '_' + str(random.SystemRandom().getrandbits(0x58))
        }
        if not stan_options:
            stan_options = {}

        self.stan_options = {**default_stan_options, **stan_options}

        app.teardown_appcontext(self.teardown)

    def teardown(self, exception):  # pylint: disable=unused-argument; flask method signature
        """Destroy all objects created by this extension."""
        try:
            this_loop = asyncio.get_event_loop()
            this_loop.run_until_complete(self.close())
        except Exception as e:
            self.logger.error(e)

    async def connect(self):
        """Connect to the queueing service."""
        ctx = _app_ctx_stack.top
        if ctx:
            if not hasattr(ctx, 'nats'):
                ctx.nats = NATS()
                ctx.stan = STAN()

            if not ctx.nats.is_connected:
                self.stan_options = {**self.stan_options, **{'nats': ctx.nats}}
                await ctx.nats.connect(**self.nats_options)
                await ctx.stan.connect(**self.stan_options)

    async def close(self):
        """Close the connections to the queue."""
        if self.nats and self.nats.is_connected:
            await self.stan.close()
            await self.nats.close()

    def publish_json(self, payload=None):
        """Publish the json payload to the Queue Service."""
        try:
            self.loop.run_until_complete(self.async_publish_json(payload))
        except Exception as err:
            self.logger.error('Error: %s', err)
            raise err

    async def async_publish_json(self, payload=None):
        """Publish the json payload to the Queue Service."""
        if not self.is_connected:
            await self.connect()

        await self.stan.publish(subject=self.subject,
                                payload=json.dumps(payload).encode('utf-8'))

    async def on_error(self, e):
        """Handle errors raised by the client library."""
        self.logger.warning('Error: %s', e)

    async def on_reconnect(self):
        """Invoke by the client library when attempting to reconnect to NATS."""
        self.logger.warning('Reconnected to NATS at nats://%s', self.nats.connected_url.netloc if self.nats else 'none')

    async def on_disconnect(self):
        """Invoke by the client library when disconnected from NATS."""
        self.logger.warning('Disconnected from NATS')

    async def on_close(self):
        """Invoke by the client library when the NATS connection is closed."""
        self.logger.warning('Closed connection to NATS')

    @property
    def is_closed(self):
        """Return True if the connection toThe cluster is closed."""
        if self.nats:
            return self.nats.is_closed
        return True

    @property
    def is_connected(self):
        """Return True if connected to the NATS cluster."""
        if self.nats:
            return self.nats.is_connected
        return False

    @property
    def stan(self):
        """Return the STAN client for the Queue Service."""
        ctx = _app_ctx_stack.top
        if ctx:
            if not hasattr(ctx, 'stan'):
                return None
            return ctx.stan
        return None

    @property
    def nats(self):
        """Return the NATS client for the Queue Service."""
        ctx = _app_ctx_stack.top
        if ctx:
            if not hasattr(ctx, 'nats'):
                return None
            return ctx.nats
        return None
