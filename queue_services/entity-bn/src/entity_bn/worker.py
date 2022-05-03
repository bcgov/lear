# Copyright © 2022 Province of British Columbia
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
from typing import Dict

import nats
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import QueueException, logger
from flask import Flask
from legal_api import db
from legal_api.core import Filing as FilingCore
from legal_api.models import Business
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_bn import config
from entity_bn.bn_processors import registration
from entity_bn.exceptions import BNException


qsm = QueueServiceManager()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)  # pragma warning disable S4502; not valid since no api exposed
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)


async def process_event(filing_msg: Dict, flask_app: Flask):  # pylint: disable=too-many-branches,too-many-statements
    """Render the filings contained in the submission.

    Start the migration to using core/Filing
    """
    if not filing_msg or filing_msg.get('type') not in [
        'bc.registry.business.registration'
    ]:
        return None

    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        filing_core_submission = FilingCore.find_by_id(filing_msg['data']['filing']['header']['filingId'])

        if not filing_core_submission:
            raise QueueException

        filing_submission = filing_core_submission.storage
        business = Business.find_by_internal_id(filing_submission.business_id)
        if not business:
            raise QueueException

        if filing_submission.filing_type == filing_core_submission.FilingTypes.REGISTRATION.value:
            registration.process(business)


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    try:
        logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
        event_message = json.loads(msg.data.decode('utf-8'))
        logger.debug('Event Message Received: %s', event_message)
        await process_event(event_message, FLASK_APP)
    except OperationalError as err:
        logger.error('Queue Blocked - Database Issue: %s', json.dumps(event_message), exc_info=True)
        raise err  # We don't want to handle the error, as a DB down would drain the queue
    except BNException as err:
        logger.error('Queue BN Issue: %s, %s', err, json.dumps(event_message), exc_info=True)
        raise err  # We don't want to handle the error, try again after sometime
    except (QueueException, Exception) as err:  # pylint: disable=broad-except
        # Catch Exception so that any error is still caught and the message is removed from the queue
        capture_message('Queue Error:' + json.dumps(event_message), level='error')
        logger.error('Queue Error: %s, %s', err, json.dumps(event_message), exc_info=True)
