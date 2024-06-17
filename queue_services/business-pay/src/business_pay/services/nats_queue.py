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
"""Service for listening and handling Queue Messages.

This service registers interest in listening to a Queue and processing received messages.
"""
from __future__ import annotations

import asyncio
import json
from typing import Dict

import nest_asyncio
from flask import g
from nats.aio.client import Client as NATS  # noqa N814; by convention the name is NATS
from nats.aio.client import DEFAULT_CONNECT_TIMEOUT
from stan.aio.client import Client as STAN  # noqa N814; by convention the name is STAN
from flask import Flask
from flask import current_app
from structured_logging import StructuredLogging

from business_pay import Config

logger = StructuredLogging.get_logger()


async def error_cb(e):
    """Emit error message to the log stream."""
    logger.error("NATS library emitted an error. %s", e, stack_info=True)

async def default_cb(msg):
    """Default callback handler."""
    logger.error("NATS default callback happened: %s", msg)


class NatsQueue:
    """Class to manage the NATS Queue service."""

    def __init__(
        self,
        *,
        app: Flask = None,
        loop=None,
        cb_handler=None,
        nats_connection_options=None,
        stan_connection_options=None,
        subscription_options=None,
        config=None,
        name=None,
    ):
        self._start_seq = 0
        self._loop = loop
        self.cb_handler = cb_handler
        self.nats_connection_options = nats_connection_options or {}
        self.stan_connection_options = stan_connection_options or {}
        self.subscription_options = subscription_options or {}
        self.config = config
        self._name = name
        if app:
            self.init_app(
                app=app,
                loop=loop,
                cb_handler=cb_handler,
                nats_connection_options=nats_connection_options,
                stan_connection_options=stan_connection_options,
                subscription_options=subscription_options,
                config=config,
                name=name,
            )

    def init_app(
        self,
        app: Flask = None,
        loop=None,
        cb_handler=default_cb,
        nats_connection_options={},
        stan_connection_options={},
        subscription_options={},
        config=None,
        name=None,
    ):
        """Initialize the application."""
        self.app = app
        self._start_seq = 0
        self.cb_handler = cb_handler
        self._name = name
        self._error_count = 0
        self.nc = None
        self.sc = None

        nest_asyncio.apply()
        self._loop = loop or asyncio.get_event_loop()

        async def conn_lost_cb(error):
            logger.info("Connection lost:%s", error)
            for i in range(0, 100):
                try:
                    logger.info("Reconnecting, attempt=%i...", i)
                    await self.connect()
                except (
                    Exception
                ) as e:  # pylint: disable=broad-except; catch all errors from client framework
                    logger.error("Error %s", e.with_traceback(), stack_info=True)
                    continue
                break

        self._stan_conn_lost_cb = conn_lost_cb

        app.teardown_appcontext(self.teardown)

        default_nats_options = {
            'io_loop': self._loop,
            'connect_timeout': app.config.get('NATS_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT),

            # NATS handlers
            'error_cb': self.on_error,
            'closed_cb': self.on_close,
            'reconnected_cb': self.on_reconnect,
            'disconnected_cb': self.on_disconnect,
        }
        nats_options = nats_connection_options or {}
        self.nats_connection_options = {**default_nats_options,
                        **self.app.config.get('NATS_CONNECTION_OPTIONS', {}),
                        **nats_options}

        self.stan_connection_options = {
                        **self.app.config.get('STAN_CONNECTION_OPTIONS', {}),
                        **stan_connection_options}

        self.subscription_options = {
                        **self.app.config.get('SUBSCRIPTION_OPTIONS', {}),
                        **subscription_options}

    def teardown(self, exception):  # pylint: disable=unused-argument; flask method signature
        """Destroy all objects created by this extension."""
        try:
            this_loop = self._loop or asyncio.get_event_loop()
            this_loop.run_until_complete(self.close())
        except RuntimeError as e:
            self.logger.error(e)

    @property
    def is_closed(self):
        """Return True if the connection toThe cluster is closed."""
        if self.nc:
            return self.nc.is_closed
        return True

    @property
    def is_connected(self):
        """Return True if connected to the NATS cluster."""
        if self.nc:
            return self.nc.is_connected
        return False

    async def on_error(self, e):
        """Handle errors raised by the client library."""
        self.logger.warning('Error: %s', e)

    async def on_reconnect(self):
        """Invoke by the client library when attempting to reconnect to NATS."""
        self.logger.warning('Reconnected to NATS at nats://%s', self.nc.connected_url.netloc if self.nc else 'none')

    async def on_disconnect(self):
        """Invoke by the client library when disconnected from NATS."""
        self.logger.warning('Disconnected from NATS')

    async def on_close(self):
        """Invoke by the client library when the NATS connection is closed."""
        self.logger.warning('Closed connection to NATS')

    @property
    async def is_healthy(self):
        """Determine if the service is working."""
        if self.nc and self.nc.is_connected:
            return True
        self._error_count += 1
        return False

    @property
    async def is_ready(self):
        """Determine if the service is ready to perform."""
        if self.nc and self.nc.is_connected:
            return True
        return False

    @property
    def stan(self):
        """Return the STAN client for the Queue Service."""
        if not hasattr(g, 'stan'):
                return None
        return g.stan

    @property
    def nats(self):
        """Return the NATS client for the Queue Service."""
        if not hasattr(g, 'nats'):
            return None
        return g.nats

    @property
    def error_count(self):
        """Return the error count."""
        return self._error_count

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
            if not hasattr(g, 'nats'):
                g.nats = self.nc = NATS()
                g.stan = self.sc = STAN()

            if not g.nats.is_connected:
                self.stan_connection_options = {
                    **self.stan_connection_options,
                    **{'nats': g.nats}
                }
                await self.nc.connect(**self.nats_connection_options)
                await self.sc.connect(**self.stan_connection_options)
                await self.sc.subscribe(**self.subscription_options)
        except Exception as err:
            print(err)

    async def close(self):
        """Close the stream and nats connections."""
        try:
            await self.sc.close()
            await self.nc.close()
        except (
            Exception
        ) as err:  # pylint: disable=broad-except; catch all errors to log out when closing the service.
            logger.debug("error when closing the streams: %s", err, stack_info=True)

    async def publish(self, subject: str, msg: Dict):
        """Publish the msg as a JSON struct to the subject, using the streaming NATS connection."""
        await self.sc.publish(subject=subject, payload=json.dumps(msg).encode("utf-8"))
