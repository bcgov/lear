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
"""This Module processes simple cloud event messages for the emailer.
"""
from http import HTTPStatus

import requests
from flask import Blueprint, current_app, request
from simple_cloudevent import SimpleCloudEvent

from business_account.AccountService import AccountService
from business_emailer.email_processors import (
    affiliation_notification,
    agm_extension_notification,
    agm_location_change_notification,
    amalgamation_notification,
    amalgamation_out_notification,
    ar_reminder_notification,
    bn_notification,
    cease_receiver_notification,
    change_of_registration_notification,
    consent_amalgamation_out_notification,
    consent_continuation_out_notification,
    continuation_in_notification,
    continuation_out_notification,
    correction_notification,
    dissolution_notification,
    filing_notification,
    involuntary_dissolution_stage_1_notification,
    mras_notification,
    name_request,
    notice_of_withdrawal_notification,
    nr_notification,
    registration_notification,
    restoration_notification,
    special_resolution_notification,
)
from business_emailer.exceptions import EmailException, QueueException
from business_emailer.services import flags, gcp_queue, verify_gcp_jwt
from business_model.models import Filing, Furnishing

bp = Blueprint("worker", __name__)




@bp.route("/", methods=("POST",))
def worker():
    """Use endpoint to process Queue Msg objects."""
    try:
        if not request.data:
            return {}, HTTPStatus.OK

        if msg := verify_gcp_jwt(request):
            current_app.logger.info(msg)
            return {}, HTTPStatus.FORBIDDEN

        current_app.logger.info(f"Incoming raw msg: {request.data!s}")

        # 1. Get cloud event
        ce = gcp_queue.get_simple_cloud_event(request, wrapped=True)
        if not ce and not isinstance(ce, SimpleCloudEvent):
            # todo: verify this ? this is how it is done in other GCP pub sub consumers
            # Decision here is to return a 200,
            # so the event is removed from the Queue
            current_app.logger.debug(f"ignoring message, raw payload: {ce!s}")
            return {}, HTTPStatus.OK

        current_app.logger.info(f"received ce: {ce!s}")

        process_email(ce)
        return {}, HTTPStatus.OK

    # ruff: noqa: PGH004
    except QueueException as err:  # noqa B902; pylint: disable=W0703; :
        # Catch Exception so that any error is still caught and the message is removed from the queue
        current_app.logger.error("Queue Error: %s", ce, exc_info=True)
        return {}, HTTPStatus.BAD_REQUEST

    except (EmailException, Exception) as err:
        message_id = ce.id if ce else None
        current_app.logger.error("Queue Error - Generic exception: %s \n %s",
                     f"\n\nMessage with id: {message_id} has been put back on the queue for reprocessing.",
                     str(err),
                     exc_info=True)
        return {}, HTTPStatus.INTERNAL_SERVER_ERROR


def send_email(email: dict, token: str):
    """Send the email."""
    # stop processing email when payload is incompleted.
    if not email \
        or "recipients" not in email \
        or "content" not in email \
        or "body" not in email["content"]:
        current_app.logger.debug("Send email: email object(s) is empty")
        raise QueueException("Unsuccessful sending email - required email object(s) is empty.")

    if not email["recipients"] \
        or not email["content"] \
        or not email["content"]["body"]:
        current_app.logger.debug("Send email: email object(s) is missing")
        raise QueueException("Unsuccessful sending email - required email object(s) is missing. ")

    try:
        resp = requests.post(
            f"{current_app.config.get('NOTIFY_API_URL')}",
            json=email,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        if resp.status_code != HTTPStatus.OK:
            raise EmailException
    except Exception:
        # this should log the error and put the email msg back on the queue
        raise EmailException("Unsuccessful response when sending email.") from None


def process_email(ce: SimpleCloudEvent):  # pylint: disable=too-many-branches, too-many-statements # noqa: PLR0912, PLR0915
    """Process the email contained in the submission."""
    etype = ce.type
    email_msg = ce.data
    current_app.logger.debug("Attempting to process email: %s", ce.data)
    token = AccountService.get_bearer_token()
    if etype and etype == "bc.registry.names.request":
        option = email_msg.get("request", {}).get("option", None)
        if option and option in [nr_notification.Option.BEFORE_EXPIRY.value,
                                 nr_notification.Option.EXPIRED.value,
                                 nr_notification.Option.RENEWAL.value,
                                 nr_notification.Option.UPGRADE.value,
                                 nr_notification.Option.REFUND.value
                                 ]:
            email = nr_notification.process(email_msg, option)
        else:
            email = name_request.process(email_msg)
        send_email(email, token)
    elif etype and etype == "bc.registry.affiliation":
        email = affiliation_notification.process(email_msg, token)
        send_email(email, token)
    elif etype and etype == "bc.registry.bnmove":
        email = bn_notification.process_bn_move(email_msg, token)
        send_email(email, token)
    elif etype and etype == "bc.registry.dissolution":
        # Confirm the data.furnishingName
        furnishing_name = email_msg.get("furnishing", {}).get("furnishingName", None)
        if furnishing_name \
            and furnishing_name in involuntary_dissolution_stage_1_notification.PROCESSABLE_FURNISHING_NAMES:
            email = involuntary_dissolution_stage_1_notification.process(email_msg, token)
            try:
                send_email(email, token)
                # Update corresponding furnishings entry as PROCESSED
                involuntary_dissolution_stage_1_notification.post_process(email_msg,
                                                                          Furnishing.FurnishingStatus.PROCESSED)
            except Exception as _:
                # Update corresponding furnishings entry as FAILED
                involuntary_dissolution_stage_1_notification.post_process(email_msg,
                                                                          Furnishing.FurnishingStatus.FAILED)
                raise
        else:
            current_app.logger.debug("Furnishing name is not valid. Skipping processing of email_msg: %s", email_msg)
    else:
        etype = email_msg["email"]["type"]
        option = email_msg["email"]["option"]
        if etype == "businessNumber":
            email = bn_notification.process(email_msg["email"])
            send_email(email, token)
        elif etype in ["amalgamationApplication",
                       "continuationIn",
                       "incorporationApplication"] and option == "mras":
            email = mras_notification.process(email_msg["email"])
            send_email(email, token)
        elif etype == "annualReport" and option == "reminder":
            flag_on = flags.is_on("disable-specific-service-provider")
            email = ar_reminder_notification.process(email_msg["email"], token, flag_on)
            send_email(email, token)
        elif etype == "agmLocationChange" and option == Filing.Status.COMPLETED.value:
            email = agm_location_change_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "agmExtension" and option == Filing.Status.COMPLETED.value:
            email = agm_extension_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "dissolution":
            email = dissolution_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "registration":
            email = registration_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "restoration":
            email_object = restoration_notification.process(email_msg["email"], token)
            send_email(email_object, token)
        elif etype == "changeOfRegistration":
            email = change_of_registration_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "correction":
            email = correction_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "consentAmalgamationOut":
            email = consent_amalgamation_out_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "amalgamationOut":
            email = amalgamation_out_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "consentContinuationOut":
            email = consent_continuation_out_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "continuationOut":
            email = continuation_out_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "specialResolution":
            email = special_resolution_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "amalgamationApplication":
            email = amalgamation_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "continuationIn":
            email = continuation_in_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "noticeOfWithdrawal" and option == Filing.Status.COMPLETED.value:
            email = notice_of_withdrawal_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype == "ceaseReceiver" and option == Filing.Status.COMPLETED.value:
            email = cease_receiver_notification.process(email_msg["email"], token)
            send_email(email, token)
        elif etype in filing_notification.FILING_TYPE_CONVERTER:
            if etype == "annualReport" and option == Filing.Status.COMPLETED.value:
                current_app.logger.debug("No email to send for: %s", email_msg)
            else:
                email = filing_notification.process(email_msg["email"], token)
                if email:
                    send_email(email, token)
                else:
                    # should only be if this was for a coops filing
                    current_app.logger.debug("No email to send for: %s", email_msg)
        else:
            current_app.logger.debug("No email to send for: %s", email_msg)
