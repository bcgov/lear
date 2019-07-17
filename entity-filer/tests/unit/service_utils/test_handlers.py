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
"""The Unit Tests for the handlers and callbacks used by the service."""
import pytest


# @pytest.mark.asyncio
# async def test_cb_subscription_handler(app, session, stan_server, event_loop, client_id, entity_stan, future):
TEST_ERROR_MSG_DATA = [
    ('message',  # test name
     'error message',  # error message
     'error message',  # expected outcome
     ),
    ('No Message', None, 'None'),
    ('Exception', Exception('exception message'), 'exception message'),
]


@pytest.mark.parametrize('test_name,error_msg,expected', TEST_ERROR_MSG_DATA)
@pytest.mark.asyncio
async def test_error_cb(caplog, test_name, error_msg, expected):
    """Assert that the callback error handler is working as expected."""
    from entity_filer.service_utils import error_cb

    await error_cb(error_msg)

    assert expected in caplog.text


@pytest.mark.asyncio
async def test_closed_cb(caplog, create_mock_coro, event_loop):
    """Exit the session after the NATS connection is closed."""
    from entity_filer.service_utils import closed_cb

    await closed_cb()

    assert 'Connection to NATS is closed.' in caplog.text


# def signal_handler(sig_loop, sig_nc, task):
#     """Handle the signaled event and schedule the shutdown process.
#     Note: This works on *nix systems only, which is fine for deployment target.
#     """

#     if sig_nc.is_closed:
#         return
#     logger.info('Signal to Shutdown received, disconnecting ...')
#     # sig_loop.create_task(close())
#     sig_loop.create_task(task())

def test_signal_handler_task(caplog):
    """Assert handler returns if the NATS connection is closed."""
    from entity_filer.service_utils import signal_handler

    class Nc():
        was_called = 0
        @property
        def is_closed(self):
            self.was_called += 1
            return False

    class Loop():
        was_called = 0

        def create_task(self, future):
            self.was_called += 1

    def close():
        pass

    my_loop = Loop()

    signal_handler(sig_loop=my_loop, sig_nc=Nc(), task=close)

    assert my_loop.was_called == 1
    assert 'Signal to Shutdown received' in caplog.text


def test_signal_handler_already_closed(caplog, create_mock_coro):
    """Assert handler returns if the NATS connection is closed."""
    from entity_filer.service_utils import signal_handler

    class Nc():
        was_called = 0

        @property
        def is_closed(self):
            self.was_called += 1
            return True

    nc = Nc()

    signal_handler(sig_loop=None, sig_nc=nc, task=None)

    assert nc.was_called == 1
    assert 'Signal: NATS connection is closed.' in caplog.text
