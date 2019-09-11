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
"""Probe on the liveliness of the service."""
import asyncio
import logging

from aiohttp import web

from entity_filer.version import __version__


class Probes():
    """Probe to manage the liveliness of the NATS and STAN service."""

    def __init__(self, *,
                 loop=asyncio.get_event_loop(),
                 logger=logging.getLogger(),
                 host='0.0.0.0',
                 port=7070,
                 components=None
                 ):
        """Initialize the probe."""
        self.app = None
        self.loop = loop
        logger.setLevel(logging.DEBUG)
        self.logger = logger
        self.host = host
        self.port = port
        self.components = components

    async def healthz_handler(self, request):  # pylint: disable=unused-argument; framework callback
        """Health of the service."""
        if self.components:
            healthy = True
            for component in self.components:
                if not await component.is_healthy:
                    healthy = False
                    break
        else:
            healthy = False

        if healthy:
            return web.json_response({'status': 'healthy'}, status=200)

        return web.json_response({'status': 'unhealthy'}, status=503)

    async def readyz_handler(self, request):  # pylint: disable=unused-argument; framework callback
        """Readiness to serve."""
        if self.components:
            ready = True
            for component in self.components:
                if not await component.is_ready:
                    ready = False
                    break
        else:
            ready = False

        if ready:
            return web.json_response({'status': 'ready'}, status=200)

        return web.json_response({'status': 'not ready'}, status=503)

    def get_app(self):
        """Return or create the web app of the probe."""
        if self.app is None:
            self.app = web.Application(loop=self.loop)
            # Routes
            self.app.router.add_route('GET', '/healthz', self.healthz_handler)
            self.app.router.add_route('GET', '/readyz', self.readyz_handler)

        return self.app

    async def start(self):
        """Run the service."""
        self.logger.info('Starting web probe v%s', __version__)

        # Server
        app = self.get_app()
        runner = web.AppRunner(app)

        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)

        self.logger.info("Liveliness probe listening at '%s : %s'", self.host, self.port)
        await site.start()

        return {self.host, self.port}
