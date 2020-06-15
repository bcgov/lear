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
import asyncio
import datetime
import json
import os

import nats
from entity_queue_common.messages import create_filing_msg, publish_email_message
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import FilingException, QueueException, logger
from flask import Flask
from legal_api import db
from legal_api.models import Filing
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_pay import config


qsm = QueueServiceManager()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)


def extract_payment_token(msg: nats.aio.client.Msg) -> dict:
    """Return a dict of the json string in the Msg.data."""
    return json.loads(msg.data.decode('utf-8'))


def get_filing_by_payment_id(payment_id: int) -> Filing:
    """Return the outcome of Filing.get_filing_by_payment_token."""
    return Filing.get_filing_by_payment_token(str(payment_id))


async def publish_filing(filing: Filing):
    """Publish the filing message onto the NATS filing subject."""
    payload = create_filing_msg(filing.id)
    subject = APP_CONFIG.FILER_PUBLISH_OPTIONS['subject']

    await qsm.service.publish(subject, payload)


async def process_payment(payment_token, flask_app):
    """Render the payment status."""
    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():

        # try to find the filing 5 times before putting back on the queue - in case payment token ends up on the queue
        # before it is assigned to filing.
        counter = 1
        filing_submission = None
        while not filing_submission and counter <= 5:
            filing_submission = get_filing_by_payment_id(payment_token['paymentToken'].get('id'))
            counter += 1
            if not filing_submission:
                await asyncio.sleep(0.2)
        if not filing_submission:
            raise FilingException

        if filing_submission.status == Filing.Status.COMPLETED.value:
            # log and skip this
            # it shouldn't be an error, but there could be something to investigate if
            # multiple retries are happening on something that should have been completed.
            logger.warning('Queue: Attempting to reprocess business.id=%s, filing.id=%s payment=%s',
                           filing_submission.business_id, filing_submission.id, payment_token)
            capture_message(f'Queue Issue: Attempting to reprocess business.id={filing_submission.business_id},'
                            f'filing.id={filing_submission.id} payment={payment_token}')
            return

        if payment_token['paymentToken'].get('statusCode') == 'TRANSACTION_FAILED':
            # TODO: The customer has cancelled out of paying, so we could note this better
            # technically the filing is still pending payment/processing
            return

        if payment_token['paymentToken'].get('statusCode') == Filing.Status.COMPLETED.value:
            filing_submission.payment_completion_date = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            db.session.add(filing_submission)
            db.session.commit()

            if not filing_submission.effective_date or \
                    filing_submission.effective_date <= \
                    datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc):
                # if we're not a future effective date, then submit for processing
                try:
                    await publish_filing(filing_submission)
                except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
                    # mark any failure for human review
                    capture_message(
                        f'Queue Error: Failed to place filing:{filing_submission.id} on Queue with error:{err}',
                        level='error')

            try:
                await publish_email_message(
                    qsm, APP_CONFIG.EMAIL_PUBLISH_OPTIONS['subject'], filing_submission, 'filed')
            except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
                # mark any failure for human review
                capture_message(
                    f'Queue Error: Failed to place email for filing:{filing_submission.id} on Queue with error:{err}',
                    level='error')

            return

        # if we're here and haven't been able to action it,
        # then we've received an unknown status and should throw an error
        logger.error('Unknown payment status given: %s', payment_token['paymentToken'].get('statusCode'))
        raise QueueException


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    try:
        logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
        payment_token = extract_payment_token(msg)
        logger.debug('Extracted payment token: %s', payment_token)
        await process_payment(payment_token, FLASK_APP)
    except OperationalError as err:
        logger.error('Queue Blocked - Database Issue: %s', json.dumps(payment_token), exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except FilingException:
        # log to sentry and absorb the error, ie: do NOT raise it, otherwise the message would be put back on the queue
        capture_message('Queue Error: cannot find filing: %s' % json.dumps(payment_token), level='error')
        logger.error('Queue Error - cannot find filing: %s', json.dumps(payment_token), exc_info=True)
    except (QueueException, Exception):  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message('Queue Error:' + json.dumps(payment_token), level='error')
        logger.error('Queue Error: %s', json.dumps(payment_token), exc_info=True)
