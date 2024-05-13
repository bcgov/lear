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
"""Utilities used by the integration tests."""
import json
from typing import Callable

import stan


async def helper_add_payment_to_queue(
    stan_client: stan.aio.client.Client, subject: str, payment_id: str, status_code: str
):
    """Add a payment token to the Queue."""
    payload = {
        "paymentToken": {
            "id": payment_id,
            "statusCode": status_code,
            "corpTypeCode": "BC",
        }
    }
    await stan_client.publish(
        subject=subject, payload=json.dumps(payload).encode("utf-8")
    )


async def subscribe_to_queue(
    stan_client: stan.aio.client.Client,
    subject: str,
    queue: str,
    durable_name: str,
    call_back: Callable[[stan.aio.client.Msg], None],
) -> str:
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

    await stan_client.subscribe(
        subject=subject, queue=queue, durable_name=durable_name, cb=call_back
    )
    return subject
