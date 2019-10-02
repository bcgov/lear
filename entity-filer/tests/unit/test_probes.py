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
"""Test suite to ensure the liveliness probe is working correctly."""
import pytest
from aiohttp import ClientSession
from aiohttp.test_utils import unused_port

from entity_filer.probes import Probes


@pytest.mark.parametrize(
    ('test_name, mock_return, expected_code, expected_msg'),
    [
        ('healthy', True, 200, {'status': 'healthy'}),
        ('not_healthy', False, 503, {'status': 'unhealthy'}),
        ('missing_nats', None, 503, {'status': 'unhealthy'})
    ])
async def test_is_healthy(test_client, loop, test_name, mock_return, expected_code, expected_msg):
    """Assert that the health check works as expected."""
    # setup
    class Service():
        def __init__(self, mock_return):
            self.mock_return = mock_return

        @property
        async def is_healthy(self):
            return self.mock_return

    # check for special case
    if mock_return is None:
        mock_service = None
    else:
        mock_service = [Service(mock_return)]

    probe = Probes(loop=loop,
                   components=mock_service)
    client = await test_client(probe.get_app())

    # test it
    resp = await client.get('/healthz')

    # verify
    assert resp.status == expected_code
    assert expected_msg == await resp.json()


@pytest.mark.parametrize(
    ('test_name, mock_return, expected_code, expected_msg'),
    [
        ('ready', True, 200, {'status': 'ready'}),
        ('not_ready', False, 503, {'status': 'not ready'}),
        ('missing_nats', None, 503, {'status': 'not ready'})
    ])
async def test_is_ready(test_client, loop, test_name, mock_return, expected_code, expected_msg):
    """Assert that the readiness check works as expected."""
    # setup
    class Service():
        def __init__(self, mock_return):
            self.mock_return = mock_return

        @property
        async def is_ready(self):
            return self.mock_return

    if mock_return is None:
        mock_service = None
    else:
        mock_service = [Service(mock_return)]

    probe = Probes(loop=loop,
                   components=mock_service)
    client = await test_client(probe.get_app())

    # test it
    resp = await client.get('/readyz')

    # verify
    assert resp.status == expected_code
    assert expected_msg == await resp.json()


async def test_probe_web_runner(loop):
    """Assert that the web app can be started successfully."""
    probe = Probes(loop=loop, port=unused_port())
    info = await probe.start()
    print(info)
    async with ClientSession() as session:
        async with session.get(f'http://{probe.host}:{str(probe.port)}/healthz') as resp:
            r_json = await resp.json()
            print(r_json)


def test_get_app(loop):
    """Assert that get_app returns the same instance everytime."""
    probe = Probes(loop=loop, port=unused_port())
    app1 = probe.get_app()
    app2 = probe.get_app()
    assert app1 == app2
