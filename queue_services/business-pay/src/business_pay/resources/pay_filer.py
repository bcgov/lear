# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the 'License');
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
#
"""This Module processes simple cloud event messages for possible filing payments.
"""
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent
from structured_logging import StructuredLogging

from business_pay.services import create_filing_msg
from business_pay.services import create_email_msg
from business_pay.services import verify_gcp_jwt
from business_pay.services import gcp_queue
from business_pay.services import nats_queue
from business_pay.database import Filing
from business_pay.database import db

bp = Blueprint("worker", __name__)

logger = StructuredLogging.get_logger()


@bp.route("/", methods=("POST",))
async def worker():
    """Process the incoming cloud event.

    Flow
    --------
    1. Get cloud event
    2. Get filing and payment information
    3. Update model
    4. Publish to email Q
    5. Publish to filer Q, if the filing is not a FED (Effective date > now())

    Decisions on returning a 2xx or failing value to
    the Queue should be noted here:
    - Empty or garbaled messages are knocked off the Q
    - If the Filing is already marked paid, skip and knock off Q
    - Once the filing is marked paid, no errors should escape to the Q
    - If there's no matching filing, put back on Q
    """
    if not request.data:
        # logger(request, "INFO", f"No incoming raw msg.")
        return {}, HTTPStatus.OK

    if msg := verify_gcp_jwt(request):
        logger.info(msg)
        return {}, HTTPStatus.FORBIDDEN

    logger.info(f"Incoming raw msg: {str(request.data)}")

    # 1. Get cloud event
    # ##
    if not (ce := gcp_queue.get_simple_cloud_event(request, wrapped=True)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        return {}, HTTPStatus.OK
    logger.info(f"received ce: {str(ce)}")

    # 2. Get payment information
    # ##
    if (
        not (payment_token := get_payment_token(ce))
        or payment_token.status_code != "COMPLETED"
    ):
        # no payment info, or not a payment COMPLETED token, take off Q
        return {}, HTTPStatus.OK

    # 3. Update model
    # ##
    if not (
        filing := Filing.get_filing_by_payment_token(pay_token=str(payment_token.id))
    ):
        # The payment token might not be there yet, put back on Q
        return {}, HTTPStatus.NOT_FOUND

    if filing.status == Filing.Status.COMPLETED.value:
        # Already processed, so don't do anything but remove from Q
        logger.debug(f"already processed, duplicate ce: {str(ce)}")
        return {}, HTTPStatus.OK

    logger.info(f"processing payment: {payment_token.id}")

    # setting the payment_completion_date, marks the filing as paid
    filing.payment_completion_date = datetime.now(timezone.utc)
    filing.payment_status_code = "COMPLETED"
    filing.status = Filing.Status.PAID
    filing.save()

    # None of these should bail as the filing has been marked PAID
    # 4. Publish to email Q
    # ##
    with suppress(Exception):
        mail_topic = current_app.config['EMAIL_PUBLISH_OPTIONS']['subject']
        email_msg = create_email_msg(filing.id, filing.filing_type)
        await nats_queue.connect()
        await nats_queue.publish(subject=mail_topic, msg=email_msg)
        logger.info(f"publish to emailer for pay-id: {payment_token.id}")

    # 5. Publish to filer Q, if the filing is not a FED (Effective date > now())
    # ##
    with suppress(Exception):
        if filing.effective_date <= filing.payment_completion_date:
            filer_topic = current_app.config['FILER_PUBLISH_OPTIONS']['subject']
            queue_message = create_filing_msg(filing.id)
            await nats_queue.connect()
            await nats_queue.publish(subject=filer_topic, msg=queue_message)
            logger.info(f"publish to filer for pay-id: {payment_token.id}")

    logger.info(f"completed ce: {str(ce)}")
    return {}, HTTPStatus.OK


@dataclass
class PaymentToken:
    """Payment Token class"""

    id: Optional[str] = None
    status_code: Optional[str] = None
    filing_identifier: Optional[str] = None
    corp_type_code: Optional[str] = None


def get_payment_token(ce: SimpleCloudEvent):
    """Return a PaymentToken if enclosed in the cloud event."""
    # TODO move to common enums for ce.type = bc.registry.payment
    if (
        (ce.type == "bc.registry.payment")
        and (data := ce.data)
        and isinstance(data, dict)
    ):
        converted = dict_keys_to_snake_case(data)
        pt = PaymentToken(**converted)
        return pt
    return None


def dict_keys_to_snake_case(d: dict):
    """Convert the keys of a dict to snake_case"""
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    converted = {}
    for k, v in d.items():
        converted[pattern.sub("_", k).lower()] = v
    return converted
