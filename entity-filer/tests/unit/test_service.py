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
"""Test Suite to ensure the ServiceWorker wrapper is working as expected."""
import pytest

from entity_filer.service import ServiceWorker


@pytest.mark.parametrize(
    ('test_name, mock_return, expected'),
    [
        ('healthy', True, True),
        ('not_healthy', False, False),
        ('missing_nats', None, False)
    ])
@pytest.mark.asyncio
async def test_is_healthy(test_name, mock_return, expected):
    """Assert that the health property works as expected."""
    service = ServiceWorker()

    class NC():
        def __init__(self, mock_return):
            self.mock_return = mock_return

        @property
        def is_connected(self):
            return self.mock_return
    if mock_return is not None:
        service.nc = NC(mock_return)

    assert expected == await service.is_healthy


@pytest.mark.parametrize(
    ('test_name, mock_return, expected'),
    [
        ('ready', True, True),
        ('not_ready', False, False),
        ('missing_nats', None, False)
    ])
@pytest.mark.asyncio
async def test_is_ready(test_name, mock_return, expected):
    """Assert that the readiness property works as expected."""
    service = ServiceWorker()

    class NC():
        def __init__(self, mock_return):
            self.mock_return = mock_return

        @property
        def is_connected(self):
            return self.mock_return
    if mock_return is not None:
        service.nc = NC(mock_return)

    assert expected == await service.is_ready


@pytest.mark.asyncio
async def test_service_connect(stan_server, event_loop):
    """Assert that the service connects to NATS, via the readiness check."""
    service = ServiceWorker(loop=event_loop)

    assert not await service.is_ready
    try:
        await service.connect()
    except Exception as err:
        print(err)

    assert await service.is_ready
