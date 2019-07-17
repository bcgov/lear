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
"""The Test Suite to ensure queue connections are working as expected."""
import pytest
from nats.aio.client import Client as Nats
from stan.aio.client import Client as Stan
from stan.aio.errors import StanError


@pytest.mark.asyncio
async def test_queue_connection(stan_server, event_loop, client_id):
    """Assert that we connect to the queue configuration used by the tests."""
    nc = Nats()
    await nc.connect(loop=event_loop)

    sc = Stan()
    await sc.connect('test-cluster', client_id, nats=nc)

    assert sc._pub_prefix  # pylint: disable=protected-access; sc does not expose a connection check
    assert sc._conn_id  # pylint: disable=protected-access; sc does not expose a connection check

    await sc.close()  # should not close the connection
    assert nc.is_connected

    with pytest.raises(StanError):
        await sc.close()

    await nc.close()
    assert not nc.is_connected
