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
"""The unique worker functionality for this service is contained here.

The entry-point is the **cb_subscription_handler**

The design and flow leverage a few constraints that are placed upon it
by NATS Streaming and using AWAIT on the default loop.
- NATS streaming queues require one message to be processed at a time.
- AWAIT on the default loop effectively runs synchronously

If these constraints change, the use of Flask-SQLAlchemy would need to change.
Flask-SQLAlchemy currently allows the base model to be changed, or reworking
the model to a standalone SQLAlchemy usage with an async engine would need
to be pursued.
"""
import json
import os
from http import HTTPStatus

import requests
from entity_queue_common.service_utils import EmailException, QueueException
from flask import Blueprint
from flask import Flask
from flask import current_app
from flask import request
from legal_api import db
from legal_api.models import Filing
from legal_api.services.bootstrap import AccountService
from simple_cloudevent import SimpleCloudEvent
from sqlalchemy.exc import OperationalError

from entity_emailer.services import queue
from entity_emailer.services.logging import structured_log
from entity_emailer.email_processors import (
    affiliation_notification,
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

from .message_tracker import tracker as tracker_util

bp = Blueprint("worker", __name__)


async def publish_event(payload: dict):
    """Publish the email message onto the NATS event subject."""
    try:
        cloud_event = SimpleCloudEvent(
          source=__name__[: __name__.find(".")],
          subject="entity.events",
          type="Filing",
          data=payload
        )
        mailer_topic = current_app.config.get("ENTITY_MAILER_TOPIC", "mailer")
        ret = queue.publish(
          topic=mailer_topic, payload=queue.to_queue_message(cloud_event)
        )
    except Exception as err:  # noqa B902; pylint: disable=W0703; we don't want to fail out the email, so ignore all.
        structured_log(request, 'ERROR', f'Queue Publish Event Error: err={err} email msg={payload}')


def send_email(email: dict, token: str):
    """Send the email."""
    # stop processing email when payload is incompleted.
    if not email \
            or 'recipients' not in email \
            or 'content' not in email \
            or 'body' not in email['content']:
        structured_log(request, 'DEBUG', 'Send email: email object(s) is empty')
        raise QueueException('Unsuccessful sending email - required email object(s) is empty.')

    if not email['recipients'] \
            or not email['content'] \
            or not email['content']['body']:
        structured_log(request, 'DEBUG', 'Send email: email object(s) is missing')
        raise QueueException('Unsuccessful sending email - required email object(s) is missing. ')

    resp = requests.post(
        f'{current_app.get("NOTIFY_API_URL", "")}',
        json=email,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    )
    if resp.status_code != HTTPStatus.OK:
        # this should log the error and put the email msg back on the queue
        raise EmailException('Unsuccessful response when sending email.')


def process_email(email_msg: dict, flask_app: Flask):  # pylint: disable=too-many-branches, too-many-statements
    """Process the email contained in the submission."""
    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        structured_log(request, 'DEBUG', f'Attempting to process email: {email_msg}')
        token = AccountService.get_bearer_token()
        etype = email_msg.get('type', None)
        if etype and etype == 'bc.registry.names.request':
            option = email_msg.get('data', {}).get('request', {}).get('option', None)
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
        elif etype and etype == 'bc.registry.affiliation':
            email = affiliation_notification.process(email_msg, token)
            send_email(email, token)
        elif etype and etype == 'bc.registry.bnmove':
            email = bn_notification.process_bn_move(email_msg, token)
            send_email(email, token)
        else:
            etype = email_msg['email']['type']
            option = email_msg['email']['option']
            if etype == 'businessNumber':
                email = bn_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype == 'incorporationApplication' and option == 'mras':
                email = mras_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype == 'annualReport' and option == 'reminder':
                email = ar_reminder_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'dissolution':
                email = dissolution_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'registration':
                email = registration_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'restoration':
                email_object = restoration_notification.process(email_msg['email'], token)
                send_email(email_object, token)
            elif etype == 'changeOfRegistration':
                email = change_of_registration_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'correction':
                email = correction_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'consentContinuationOut':
                email = consent_continuation_out_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'continuationOut':
                email = continuation_out_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'specialResolution':
                email = special_resolution_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype in filing_notification.FILING_TYPE_CONVERTER.keys():
                if etype == 'annualReport' and option == Filing.Status.COMPLETED.value:
                    structured_log(request, 'DEBUG', f'No email to send for: {email_msg}')
                else:
                    email = filing_notification.process(email_msg['email'], token)
                    if email:
                        send_email(email, token)
                    else:
                        # should only be if this was for a a coops filing
                        structured_log(request, 'DEBUG', f'No email to send for: {email_msg}')
            else:
                structured_log(request, 'DEBUG', f'No email to send for: {email_msg}')


@bp.route("/", methods=("POST",))
def worker():
    """Process the incoming cloud event"""
    structured_log(request, "INFO", f"Incoming raw msg: {request.data}")
    
    # Get cloud event
    # ##
    if not (ce := queue.get_simple_cloud_event(request)):
        #
        # Decision here is to return a 200,
        # so the event is removed from the Queue
        return {}, HTTPStatus.OK

    structured_log(request, "INFO", f"received ce: {str(ce)}")

    with current_app.app_context():

        try:
            structured_log(request, 'INFO', f'Received raw message seq: {ce.sequence}, data=  {ce.data.decode()}')
            email_msg = json.loads(ce.data.decode('utf-8'))
            structured_log(request, 'DEBUG', f'Extracted email msg: {email_msg}')
            message_context_properties = tracker_util.get_message_context_properties(ce)
            process_message, tracker_msg = tracker_util.is_processable_message(message_context_properties)
            if process_message:
                tracker_msg = tracker_util.start_tracking_message(message_context_properties, email_msg, tracker_msg)
                process_email(email_msg, current_app)
                tracker_util.complete_tracking_message(tracker_msg)
            else:
                # Skip processing of message due to message state - previously processed or currently being
                # processed
                structured_log(request, 'DEBUG', f'Skipping processing of email_msg: {email_msg}')
        except OperationalError as err:
            structured_log(request, 'ERROR', f'Queue Blocked - Database Issue: {json.dumps(email_msg)}')
            error_details = f'OperationalError - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
            raise err  # We don't want to handle the error, as a DB down would drain the queue
        except EmailException as err:
            structured_log(request, 'ERROR', f'Queue Error - email failed to send: {json.dumps(email_msg)}'
                         '\n\nThis message has been put back on the queue for reprocessing.')
            error_details = f'EmailException - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
            raise err  # we don't want to handle the error, so that the message gets put back on the queue
        except (QueueException, Exception) as err:  # noqa B902; pylint: disable=W0703;
            # Catch Exception so that any error is still caught and the message is removed from the queue
            structured_log(request, 'ERROR', f'Queue Error: {json.dumps(email_msg)}')
            error_details = f'QueueException, Exception - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
