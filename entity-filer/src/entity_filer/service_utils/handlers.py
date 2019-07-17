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
"""Callbacks and signal trapping used in the main loop."""
import asyncio

# from entity_filer.service.service_logger import logger
from .service_logger import logger


async def error_cb(e):
    """Emit error message to the log stream."""
    logger.error(e)


async def closed_cb():
    """Exit the session after the NATS connection is closed."""
    logger.info('Connection to NATS is closed.')
    my_loop = asyncio.get_running_loop()
    await asyncio.sleep(0.1, loop=my_loop)
    my_loop.stop()


def signal_handler(sig_loop, sig_nc, task):
    """Handle the signaled event and schedule the shutdown process.

    Note: This works on *nix systems only, which is fine for deployment target.
    """
    if sig_nc.is_closed:
        logger.info('Signal: NATS connection is closed.')
        return
    logger.info('Signal to Shutdown received, disconnecting ...')
    sig_loop.create_task(task())
