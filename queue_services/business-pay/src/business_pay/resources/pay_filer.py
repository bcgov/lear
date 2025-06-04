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
import traceback
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent
from simple_cloudevent import to_queue_message
from structured_logging import StructuredLogging

from business_pay.database import Filing
from business_pay.services import create_email_msg
from business_pay.services import create_filing_msg
from business_pay.services import create_gcp_filing_msg
from business_pay.services import flags
from business_pay.services import gcp_queue
from business_pay.services import queue
from business_pay.services import verify_gcp_jwt

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
    4. Publish to filer Q, if the filing is not a FED (Effective date > now())
    5. Publish to email Q

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
    if not (ce := gcp_queue.get_simple_cloud_event(request,
                                                   wrapped=True)) \
            and not isinstance(ce, SimpleCloudEvent):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        logger.debug(f"ignoring message, raw payload: {str(ce)}")
        return {}, HTTPStatus.OK
    logger.info(f"received ce: {str(ce)}")

    # 2. Get payment information
    # ##
    if (
        not (payment_token := get_payment_token(ce))
        or payment_token.status_code != "COMPLETED"
    ):
        # no payment info, or not a payment COMPLETED token, take off Q
        logger.debug(f"Removed From Queue: no payment info in ce: {str(ce)}")
        return {}, HTTPStatus.OK

    if payment_token.corp_type_code in ["MHR", "BCR", "BTR", "BUS", "STRR"]:
        logger.debug(
            f"ignoring message for corp_type_code:{payment_token.corp_type_code},  {str(ce)}")
        return {}, HTTPStatus.OK

    logger.debug(f"Payment Token: {payment_token} for : {str(ce)}")

    # 3. Update model
    # ##
    if not (
        filing := Filing.get_filing_by_payment_token(pay_token=str(payment_token.id))
    ):
        if payment_token.filing_identifier is None and \
           payment_token.corp_type_code == "BC":
            logger.debug(
                f"Take Off Queue - BOGUS Filing Not Found: {payment_token} for : {str(ce)}")
            return {}, HTTPStatus.OK

        logger.debug(
            f"Put Back on Queue - Filing Not Found: {payment_token} for : {str(ce)}")
        # The payment token might not be there yet, put back on Q
        return {}, HTTPStatus.NOT_FOUND

    if filing.payment_completion_date:
        # Already processed, so don't do anything but remove from Q
        logger.debug(f"already processed, duplicate ce: {str(ce)}")
        return {}, HTTPStatus.OK

    logger.info(f"processing payment: {payment_token.id}")

    # setting the payment_completion_date, marks the filing as paid
    # in the unlikely event that the CE time is null, use now()
    filing.payment_completion_date = ce.time or datetime.now(timezone.utc)
    filing.payment_status_code = "COMPLETED"
    filing.status = Filing.Status.PAID
    filing.save()

    # 4. Publish to filer Q, if the filing is not a FED (Effective date > now())
    # ##
    publish_to_filer(filing, payment_token)

    # None of these should bail as the filing has been marked PAID
    # 5. Publish to email Q
    # ##
    publish_to_emailer(filing)

    logger.info(f"completed ce: {str(ce)}")
    return {}, HTTPStatus.OK


@dataclass
class PaymentToken:
    """Payment Token class"""

    id: Optional[str] = None
    status_code: Optional[str] = None
    filing_identifier: Optional[str] = None
    corp_type_code: Optional[str] = None


def publish_to_filer(filing: Filing, payment_token: PaymentToken):
    """Publish a queue message to entity-filer once the filing has been marked as PAID."""
    logger.debug(
        f"checking filer for pay-id: {payment_token.id} on filing: {filing}")
    try:
        if filing.effective_date <= filing.payment_completion_date:
            # use Pub/Sub if in GCP, otherwise NATS
            if current_app.config['DEPLOYMENT_PLATFORM'] == 'GCP':
                data = create_gcp_filing_msg(filing.id)

                ce = SimpleCloudEvent(
                    id=str(uuid.uuid4()),
                    source='business_pay',
                    subject='filing',
                    time=datetime.now(timezone.utc),
                    type='filingMessage',
                    data = data
                )
                topic = current_app.config.get('BUSINESS_FILER_TOPIC')
                gcp_queue.publish(topic, to_queue_message(ce))
                logger.debug(
                    f"Filer pub/sub message: {str(ce)}"
                )
            else:
                filer_topic = current_app.config["FILER_PUBLISH_OPTIONS"]["subject"]
                queue_message = create_filing_msg(filing.id)
                logger.debug(f"Filer NATS message: {queue_message}")
                # await queue.publish(subject=filer_topic, msg=queue_message)
                queue.publish_json(subject=filer_topic, payload=queue_message)

        logger.info(f"publish to filer for pay-id: {payment_token.id}")
    except Exception as err:
        logger.debug(
            f"Publish to Filer error: {err}, for pay-id: {payment_token.id}")
        # debug
        logger.debug(traceback.format_exc())


def publish_to_emailer(filing: Filing):
    """Publish a queue message to entity-emailer once the filing has been marked as PAID."""
    with suppress(Exception):
        # skip publishing NATS message
        if flags.is_on("enable-sandbox"):
            logger.debug("Skip publishing to emailer.")
            return

        email_msg = create_email_msg(filing.id, filing.filing_type)

        if current_app.config['DEPLOYMENT_PLATFORM'] == 'GCP':
            ce = SimpleCloudEvent(
                id=str(uuid.uuid4()),
                source='business_pay',
                subject='filing',
                time=datetime.now(timezone.utc),
                data=email_msg
            )
            topic = current_app.config.get('BUSINESS_EMAILER_TOPIC')
            gcp_queue.publish(topic, to_queue_message(ce))
            logger.debug(f"Emailer pub/sub message: {str(ce)}")
        else:
            mail_topic = current_app.config["EMAIL_PUBLISH_OPTIONS"]["subject"]
            # await queue.publish(subject=mail_topic, msg=email_msg)
            queue.publish_json(subject=mail_topic, payload=email_msg)
            logger.info(
                f"published to emailer for filing-id: {filing.id}")


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
