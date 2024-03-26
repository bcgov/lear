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
"""This Module processes simple cloud event messages for possible filing payments
"""
import json
from http import HTTPStatus

import requests
from flask import Blueprint, current_app, request
from legal_api.models import Filing
from legal_api.services.bootstrap import AccountService
from legal_api.services.flags import Flags

from entity_emailer.email_processors import (
    affiliation_notification,
    agm_extension_notification,
    agm_location_change_notification,
    amalgamation_notification,
    ar_reminder_notification,
    bn_notification,
    change_of_registration_notification,
    consent_continuation_out_notification,
    continuation_out_notification,
    correction_notification,
    dissolution_notification,
    filing_notification,
    mras_notification,
    name_request,
    nr_notification,
    registration_notification,
    restoration_notification,
    special_resolution_notification,
)
from entity_emailer.services import queue
from entity_emailer.services.logging import structured_log

bp = Blueprint("worker", __name__)


@bp.route("/", methods=("POST",))
def worker():
    """Process the incoming cloud event
    Flow
    --------
    1. Get cloud event
    2. Get email message
    3. Process email
    4. Send email

    Decisions on returning a 2xx or failing value to
    the Queue should be noted here:
    - Empty or garbaled messages are knocked off the Q
    - If there is no email to send, knock off Q
    - If email object(s) are empty or missing, knock off Q
    - If email failed to send, put back on Q
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

    # 2. Get email message
    # ##
    if not (email_msg := json.loads(ce.data.decode("utf-8"))):
        # no email message, take off queue
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"Extracted email msg: {email_msg}")

    # 3. Process email
    # ##
    token = AccountService.get_bearer_token()
    if not (email := process_email(email_msg, token)):
        # no email to send, take off queue
        structured_log(request, "INFO", f"No email to send for: {email_msg}")
        return {}, HTTPStatus.OK

    # 4. Send email
    # ##
    if not email or "recipients" not in email or "content" not in email or "body" not in email["content"]:
        # email object(s) is empty, take off queue
        structured_log(request, "INFO", "Send email: email object(s) is empty")
        return {}, HTTPStatus.OK

    if not email["recipients"] or not email["content"] or not email["content"]["body"]:
        # email object(s) is missing, take off queue
        structured_log(request, "INFO", "Send email: email object(s) is missing")
        return {}, HTTPStatus.OK

    resp = send_email(email, token)

    if resp.status_code != HTTPStatus.OK:
        # log the error and put the email msg back on the queue
        structured_log(
            request,
            "ERROR",
            f"Queue Error - email failed to send: {json.dumps(email_msg)}"
            "\n\nThis message has been put back on the queue for reprocessing.",
        )
        return {}, HTTPStatus.NOT_FOUND

    structured_log(request, "INFO", f"completed ce: {str(ce)}")
    return {}, HTTPStatus.OK


def process_email(email_msg: dict, token: str):  # pylint: disable=too-many-branches, too-many-statements
    """Process the email contained in the submission."""
    flags = Flags()
    if current_app.config.get("LD_SDK_KEY", None):
        flags.init_app(current_app)

    structured_log(request, "DEBUG", f"Attempting to process email: {email_msg}")
    etype = email_msg.get("type", None)
    if etype and etype == "bc.registry.names.request":
        option = email_msg.get("data", {}).get("request", {}).get("option", None)
        if option and option in [
            nr_notification.Option.BEFORE_EXPIRY.value,
            nr_notification.Option.EXPIRED.value,
            nr_notification.Option.RENEWAL.value,
            nr_notification.Option.UPGRADE.value,
            nr_notification.Option.REFUND.value,
        ]:
            email = nr_notification.process(email_msg, option)
        else:
            email = name_request.process(email_msg)
    elif etype and etype == "bc.registry.affiliation":
        email = affiliation_notification.process(email_msg, token)
    elif etype and etype == "bc.registry.bnmove":
        email = bn_notification.process_bn_move(email_msg, token)
    else:
        etype = email_msg["email"]["type"]
        option = email_msg["email"]["option"]
        if etype == "businessNumber":
            email = bn_notification.process(email_msg["email"])
        elif etype == "incorporationApplication" and option == "mras":
            email = mras_notification.process(email_msg["email"])
        elif etype == "annualReport" and option == "reminder":
            flag_on = flags.value("disable-specific-service-provider")
            email = ar_reminder_notification.process(email_msg["email"], token, flag_on)
        elif etype == "agmLocationChange" and option == Filing.Status.COMPLETED.value:
            email = agm_location_change_notification.process(email_msg["email"], token)
        elif etype == "agmExtension" and option == Filing.Status.COMPLETED.value:
            email = agm_extension_notification.process(email_msg["email"], token)
        elif etype == "dissolution":
            email = dissolution_notification.process(email_msg["email"], token)
        elif etype == "registration":
            email = registration_notification.process(email_msg["email"], token)
        elif etype == "restoration":
            email = restoration_notification.process(email_msg["email"], token)
        elif etype == "changeOfRegistration":
            email = change_of_registration_notification.process(email_msg["email"], token)
        elif etype == "correction":
            email = correction_notification.process(email_msg["email"], token)
        elif etype == "consentContinuationOut":
            email = consent_continuation_out_notification.process(email_msg["email"], token)
        elif etype == "continuationOut":
            email = continuation_out_notification.process(email_msg["email"], token)
        elif etype == "specialResolution":
            email = special_resolution_notification.process(email_msg["email"], token)
        elif etype == "amalgamationApplication":
            email = amalgamation_notification.process(email_msg["email"], token)
        # pylint: disable-next=consider-iterating-dictionary
        elif etype in filing_notification.FILING_TYPE_CONVERTER.keys():
            if etype == "annualReport" and option == Filing.Status.COMPLETED.value:
                return None
            else:
                email = filing_notification.process(email_msg["email"], token)
                if not email:  # should only be if this was for a a coops filing
                    return None
        else:
            return None
    return email


def send_email(email: dict, token: str):
    """Send the email"""
    return requests.post(
        f'{current_app.get("NOTIFY_API_URL", "")}',
        json=email,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
