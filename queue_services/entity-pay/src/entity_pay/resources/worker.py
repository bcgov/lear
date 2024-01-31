# Copyright © 2023 Province of British Columbia
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
import datetime
import re
from contextlib import suppress
from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional

from flask import Blueprint, current_app, request
from legal_api.models import Filing
from simple_cloudevent import SimpleCloudEvent

from entity_pay.services import queue
from entity_pay.services.logging import structured_log

bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():
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
    structured_log(request, "INFO", f"Incoming raw msg: {request.data}")

    # 1. Get cloud event
    # ##
    if not (ce := queue.get_simple_cloud_event(request)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"received ce: {str(ce)}")

    # 2. Get payment information
    # ##
    if not (payment_token := get_payment_token(ce)) or payment_token.status_code != "COMPLETED":
        # no payment info, or not a payment COMPLETED token, take off Q
        return {}, HTTPStatus.OK

    # 3. Update model
    # ##
    if not (filing := get_filing_by_payment_id(int(payment_token.id))):
        # The payment token might not be there yet, put back on Q
        return {}, HTTPStatus.NOT_FOUND

    if filing.status == Filing.Status.COMPLETED.value:
        # Already processed, so don't do anything but remove from Q
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"processing payment: {payment_token.id}")

    # setting the payment_completion_date, marks the filing as paid
    filing.payment_completion_date = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    filing.save()

    # None of these should bail as the filing has been marked PAID
    cloud_event = SimpleCloudEvent(
        source=__name__[: __name__.find(".")],
        subject="filing",
        type="Filing",
        data={
            "filingId": filing.id,
            "filingType": filing.filing_type,
            "filingEffectiveDate": filing.effective_date.isoformat(),
        },
    )
    # None of these should bail as the filing has been marked PAID
    # 4. Publish to email Q
    # ##
    with suppress(Exception):
        mail_topic = current_app.config.get("ENTITY_MAILER_TOPIC", "mailer")
        # pylint: disable-next=unused-variable
        ret = queue.publish(topic=mail_topic, payload=queue.to_queue_message(cloud_event))
        structured_log(request, "INFO", f"publish to emailer for pay-id: {payment_token.id}")

    # 5. Publish to filer Q, if the filing is not a FED (Effective date > now())
    # ##
    with suppress(Exception):
        if filing.effective_date <= filing.payment_completion_date:
            filer_topic = current_app.config.get("ENTITY_FILER_TOPIC", "filer")
            ret = queue.publish(topic=filer_topic, payload=queue.to_queue_message(cloud_event))  # noqa: F841
            structured_log(request, "INFO", f"publish to filer for pay-id: {payment_token.id}")

    structured_log(request, "INFO", f"completed ce: {str(ce)}")
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
    if (
        (ce.type == "payment")
        and (data := ce.data)
        and isinstance(data, dict)
        and (payment_token := data.get("paymentToken", {}))
    ):
        converted = dict_keys_to_snake_case(payment_token)
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


def get_filing_by_payment_id(payment_id: int) -> Filing:
    """Return the outcome of Filing.get_filing_by_payment_token."""
    return Filing.get_filing_by_payment_token(str(payment_id))
