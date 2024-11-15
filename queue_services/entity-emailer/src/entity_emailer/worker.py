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

import nats
import requests
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import EmailException, QueueException, logger
from flask import Flask
from legal_api import db
from legal_api.models import Filing, Furnishing
from legal_api.services.bootstrap import AccountService
from legal_api.services.flags import Flags
from sqlalchemy.exc import OperationalError

from entity_emailer import config
from entity_emailer.email_processors import (
    affiliation_notification,
    agm_extension_notification,
    agm_location_change_notification,
    amalgamation_notification,
    ar_reminder_notification,
    bn_notification,
    change_of_registration_notification,
    consent_continuation_out_notification,
    continuation_in_notification,
    continuation_out_notification,
    correction_notification,
    dissolution_notification,
    filing_notification,
    involuntary_dissolution_stage_1_notification,
    mras_notification,
    name_request,
    nr_notification,
    registration_notification,
    restoration_notification,
    special_resolution_notification,
)

from .message_tracker import tracker as tracker_util


qsm = QueueServiceManager()  # pylint: disable=invalid-name
flags = Flags()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)

if FLASK_APP.config.get('LD_SDK_KEY', None):
    flags.init_app(FLASK_APP)


async def publish_event(payload: dict):
    """Publish the email message onto the NATS event subject."""
    try:
        subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']
        await qsm.service.publish(subject, payload)
    except Exception as err:  # noqa B902; pylint: disable=W0703; we don't want to fail out the email, so ignore all.
        logger.error('Queue Publish Event Error: err=%s email msg=%s', err, payload, exc_info=True)


def send_email(email: dict, token: str):
    """Send the email."""
    # stop processing email when payload is incompleted.
    if not email \
            or 'recipients' not in email \
            or 'content' not in email \
            or 'body' not in email['content']:
        logger.debug('Send email: email object(s) is empty')
        raise QueueException('Unsuccessful sending email - required email object(s) is empty.')

    if not email['recipients'] \
            or not email['content'] \
            or not email['content']['body']:
        logger.debug('Send email: email object(s) is missing')
        raise QueueException('Unsuccessful sending email - required email object(s) is missing. ')

    try:
        resp = requests.post(
            f'{APP_CONFIG.NOTIFY_API_URL}',
            json=email,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        if resp.status_code != HTTPStatus.OK:
            raise EmailException
    except Exception:  # noqa B902; pylint: disable=W0703; we don't want to fail out the email, so ignore all.
        # this should log the error and put the email msg back on the queue
        raise EmailException('Unsuccessful response when sending email.')


def process_email(email_msg: dict, flask_app: Flask):  # pylint: disable=too-many-branches, too-many-statements
    """Process the email contained in the submission."""
    if not flask_app:
        raise QueueException('Flask App not available.')
    # Debugging logger for #24361, will have another PR before closing the ticket to remove it
    flask_app.logger.debug(f'\U0001F4D2 email_msg: {email_msg}')
    # debugging logger end
    with flask_app.app_context():
        logger.debug('Attempting to process email: %s', email_msg)
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
        elif etype and etype == 'bc.registry.dissolution':
            # Confirm the data.furnishingName
            furnishing_name = email_msg.get('data', {}).get('furnishing', {}).get('furnishingName', None)
            if furnishing_name \
                    and furnishing_name in involuntary_dissolution_stage_1_notification.PROCESSABLE_FURNISHING_NAMES:
                email = involuntary_dissolution_stage_1_notification.process(email_msg, token)
                try:
                    send_email(email, token)
                    # Update corresponding furnishings entry as PROCESSED
                    involuntary_dissolution_stage_1_notification.post_process(email_msg,
                                                                              Furnishing.FurnishingStatus.PROCESSED)
                except Exception as _:  # noqa B902; pylint: disable=W0703
                    # Update corresponding furnishings entry as FAILED
                    involuntary_dissolution_stage_1_notification.post_process(email_msg,
                                                                              Furnishing.FurnishingStatus.FAILED)
                    raise
            else:
                logger.debug('Furnishing name is not valid. Skipping processing of email_msg: %s', email_msg)
        else:
            etype = email_msg['email']['type']
            option = email_msg['email']['option']
            if etype == 'businessNumber':
                email = bn_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype in ['amalgamationApplication',
                           'continuationIn',
                           'incorporationApplication'] and option == 'mras':
                email = mras_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype == 'annualReport' and option == 'reminder':
                flag_on = flags.is_on('disable-specific-service-provider')
                email = ar_reminder_notification.process(email_msg['email'], token, flag_on)
                send_email(email, token)
            elif etype == 'agmLocationChange' and option == Filing.Status.COMPLETED.value:
                email = agm_location_change_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'agmExtension' and option == Filing.Status.COMPLETED.value:
                email = agm_extension_notification.process(email_msg['email'], token)
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
            elif etype == 'amalgamationApplication':
                email = amalgamation_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype == 'continuationIn':
                email = continuation_in_notification.process(email_msg['email'], token)
                send_email(email, token)
            elif etype in filing_notification.FILING_TYPE_CONVERTER.keys():
                if etype == 'annualReport' and option == Filing.Status.COMPLETED.value:
                    logger.debug('No email to send for: %s', email_msg)
                else:
                    email = filing_notification.process(email_msg['email'], token)
                    if email:
                        send_email(email, token)
                    else:
                        # should only be if this was for a a coops filing
                        logger.debug('No email to send for: %s', email_msg)
            else:
                logger.debug('No email to send for: %s', email_msg)


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    with FLASK_APP.app_context():

        try:
            logger.info('Received raw message seq: %s, data=  %s', msg.sequence, msg.data.decode())
            email_msg = json.loads(msg.data.decode('utf-8'))
            logger.debug('Extracted email msg: %s', email_msg)
            message_context_properties = tracker_util.get_message_context_properties(msg)
            process_message, tracker_msg = tracker_util.is_processable_message(message_context_properties)
            if process_message:
                tracker_msg = tracker_util.start_tracking_message(message_context_properties, email_msg, tracker_msg)
                process_email(email_msg, FLASK_APP)
                tracker_util.complete_tracking_message(tracker_msg)
            else:
                # Skip processing of message due to message state - previously processed or currently being
                # processed
                logger.debug('Skipping processing of email_msg: %s', email_msg)
        except OperationalError as err:
            logger.error('Queue Blocked - Database Issue: %s', json.dumps(email_msg), exc_info=True)
            error_details = f'OperationalError - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
            raise err  # We don't want to handle the error, as a DB down would drain the queue
        except EmailException as err:
            logger.error('Queue Error - email failed to send: %s'
                         '\n\nThis message has been put back on the queue for reprocessing.',
                         json.dumps(email_msg), exc_info=True)
            error_details = f'EmailException - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
            raise err  # we don't want to handle the error, so that the message gets put back on the queue
        except (QueueException, Exception) as err:  # noqa B902; pylint: disable=W0703;
            # Catch Exception so that any error is still caught and the message is removed from the queue
            logger.error('Queue Error: %s', json.dumps(email_msg), exc_info=True)
            error_details = f'QueueException, Exception - {str(err)}'
            tracker_util.mark_tracking_message_as_failed(message_context_properties,
                                                         email_msg,
                                                         tracker_msg,
                                                         error_details)
