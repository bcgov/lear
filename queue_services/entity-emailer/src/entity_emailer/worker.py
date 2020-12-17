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
from legal_api.models import Filing
from legal_api.services.bootstrap import AccountService
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_emailer import config
from entity_emailer.email_processors import bn_notification, filing_notification, mras_notification, name_request


qsm = QueueServiceManager()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)


async def publish_event(payload: dict):
    """Publish the email message onto the NATS event subject."""
    try:
        subject = APP_CONFIG.ENTITY_EVENT_PUBLISH_OPTIONS['subject']
        await qsm.service.publish(subject, payload)
    except Exception as err:  # pylint: disable=broad-except; we don't want to fail out the email, so ignore all.
        capture_message(f'Queue Publish Event Error: email msg={payload}, error={err}', level='error')
        logger.error('Queue Publish Event Error: email msg=%s', payload, exc_info=True)


def send_email(email: dict, token: str):
    """Send the email."""
    resp = requests.post(
        f'{APP_CONFIG.NOTIFY_API_URL}',
        json=email,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    )
    if resp.status_code != HTTPStatus.OK:
        # this should log the error and put the email msg back on the queue
        raise EmailException('Unsuccessful response when sending email.')


def process_email(email_msg: dict, flask_app: Flask):  # pylint: disable=too-many-branches
    """Process the email contained in the submission."""
    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        logger.debug('Attempting to process email: %s', email_msg)
        token = AccountService.get_bearer_token()
        etype = email_msg['email']['type']
        if etype == 'bc.registry.namex.request':
            email = name_request.process(email_msg)
            send_email(email, token)
        else:
            option = email_msg['email']['option']
            if etype == 'businessNumber':
                email = bn_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype == 'incorporationApplication' and option == 'mras':
                email = mras_notification.process(email_msg['email'])
                send_email(email, token)
            elif etype in filing_notification.FILING_TYPE_CONVERTER.keys():
                if etype == 'annualReport' and option == Filing.Status.COMPLETED.value:
                    logger.debug('No email to send for: %s', email_msg)
                # Remove this when self serve alteration is implemented.
                elif etype == 'alteration' and option == Filing.Status.PAID.value:
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
    try:
        logger.info('Received raw message seq: %s, data=  %s', msg.sequence, msg.data.decode())
        email_msg = json.loads(msg.data.decode('utf-8'))
        logger.debug('Extracted email msg: %s', email_msg)
        process_email(email_msg, FLASK_APP)
    except OperationalError as err:
        logger.error('Queue Blocked - Database Issue: %s', json.dumps(email_msg), exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except EmailException as err:
        logger.error('Queue Error - email failed to send: %s'
                     '\n\nThis message has been put back on the queue for reprocessing.',
                     json.dumps(email_msg), exc_info=True)
        raise err  # we don't want to handle the error, so that the message gets put back on the queue
    except (QueueException, Exception):  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message('Queue Error: ' + json.dumps(email_msg), level='error')
        logger.error('Queue Error: %s', json.dumps(email_msg), exc_info=True)
