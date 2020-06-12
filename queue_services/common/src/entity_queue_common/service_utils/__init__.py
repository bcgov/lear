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
"""Callbacks and utility functions used to support the service loop."""
from typing import Callable

import stan

from .exceptions import EmailException, FilingException, QueueException
from .handlers import error_cb, signal_handler
from .run_version import get_run_version
from .service_logger import logger


async def subscribe_to_queue(stan_client: stan.aio.client.Client,
                             subject: str,
                             queue: str,
                             durable_name: str,
                             call_back: Callable[[stan.aio.client.Msg], None]) \
        -> str:
    """Subscribe to the Queue using the environment setup.

    Args:
        stan_client: the stan connection
        call_back: a callback function that accepts 1 parameter, a Msg
    Returns:
       str: the name of the queue
    """
    # entity_subject = os.getenv('LEGAL_FILING_STAN_SUBJECT')
    # entity_queue = os.getenv('LEGAL_FILING_STAN_QUEUE')
    # entity_durable_name = os.getenv('LEGAL_FILING_STAN_DURABLE_NAME')

    await stan_client.subscribe(subject=subject,
                                queue=queue,
                                durable_name=durable_name,
                                cb=call_back)
    return subject
