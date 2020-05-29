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

import nats
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import EmailException, QueueException, logger
from flask import Flask
from legal_api import db
# from legal_api.models import Business
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_emailer import config
from entity_emailer.email_processors import bn_notification, incorp_notification


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
    except Exception as err:  # pylint: disable=broad-except; we don't want to fail out the filing, so ignore all.
        capture_message(f'Queue Publish Event Error: email msg={payload}, error={err}', level='error')
        logger.error('Queue Publish Event Error: email msg=%s', payload, exc_info=True)


def process_email(email_msg: dict, flask_app: Flask):  # pylint: disable=too-many-branches
    """Process the email contained in the submission."""
    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        logger.debug('Attempting to process email: %s', email_msg)
        email = None
        if email_msg['email']['type'] == 'bn':
            email = bn_notification.process(email_msg)
        elif email_msg['email']['type'] == 'incorp':
            email = incorp_notification.process(email_msg)
        else:
            raise EmailException(f'Unrecognizable type: {email_msg["email"]["type"]}')
        # TODO: send email via email service
        logger.debug('NI: Sending email: %s', email)
        return


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    try:
        logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
        email_msg = json.loads(msg.data.decode('utf-8'))
        logger.debug('Extracted email msg: %s', email_msg)
        process_email(email_msg, FLASK_APP)
    except OperationalError as err:
        logger.error('Queue Blocked - Database Issue: %s', json.dumps(email_msg), exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except EmailException as err:
        logger.error('Queue Error - cannot find email template: %s'
                     '\n\nThis message has been put back on the queue for reprocessing.',
                     json.dumps(email_msg), exc_info=True)
        raise err  # we don't want to handle the error, so that the message gets put back on the queue
    except (QueueException, Exception):  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message('Queue Error:' + json.dumps(email_msg), level='error')
        logger.error('Queue Error: %s', json.dumps(email_msg), exc_info=True)
