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
import uuid
from typing import Dict

import nats
from entity_queue_common.service_utils import QueueException, logger
from flask import Flask
from legal_api import db
from legal_api.core import Filing as FilingCore
from legal_api.models import Business
from legal_api.utils.datetime import datetime
from sentry_sdk import capture_message
from sqlalchemy.exc import OperationalError

from entity_bn import config
from entity_bn.bn_processors import (  # noqa: I001
    admin,
    change_of_registration,
    correction,
    dissolution_or_put_back_on,
    publish_event,
    registration,
)
from entity_bn.exceptions import BNException


APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)  # pragma: no cover
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)


async def process_event(msg: Dict, flask_app: Flask):  # pylint: disable=too-many-branches,too-many-statements
    """Process CRA request."""
    if not msg or msg.get('type') not in [
        'bc.registry.business.registration',
        'bc.registry.business.changeOfRegistration',
        'bc.registry.business.correction',
        'bc.registry.business.dissolution',
        'bc.registry.business.putBackOn',
        'bc.registry.admin.bn'
    ]:
        return None

    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        if msg['type'] == 'bc.registry.admin.bn':
            await admin.process(msg)
            return msg['data']['business']['identifier']

        filing_core_submission = FilingCore.find_by_id(msg['data']['filing']['header']['filingId'])
        if not filing_core_submission:
            raise QueueException

        filing_submission = filing_core_submission.storage
        business = Business.find_by_internal_id(filing_submission.business_id)
        if not business:
            raise QueueException

        if filing_submission.filing_type == filing_core_submission.FilingTypes.REGISTRATION.value:
            await registration.process(business)
        elif filing_submission.filing_type == filing_core_submission.FilingTypes.CHANGEOFREGISTRATION.value:
            change_of_registration.process(business, filing_core_submission.storage)
        elif filing_submission.filing_type == filing_core_submission.FilingTypes.CORRECTION.value and \
                business.legal_type in (Business.LegalTypes.SOLE_PROP.value,
                                        Business.LegalTypes.PARTNERSHIP.value):
            correction.process(business, filing_core_submission.storage)
        elif filing_submission.filing_type in (filing_core_submission.FilingTypes.DISSOLUTION.value,
                                               filing_core_submission.FilingTypes.PUTBACKON.value) and \
                business.legal_type in (Business.LegalTypes.SOLE_PROP.value,
                                        Business.LegalTypes.PARTNERSHIP.value):
            dissolution_or_put_back_on.process(business, filing_core_submission.storage)

        return business.identifier


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    try:
        logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
        event_message = json.loads(msg.data.decode('utf-8'))
        logger.debug('Event Message Received: %s', event_message)
        identifier = await process_event(event_message, FLASK_APP)
        # publish identifier (so other things know business has changed)
        try:
            payload = {
                'specversion': '1.x-wip',
                'type': 'bc.registry.business.bn',
                'source': 'entity-bn.cb_subscription_handler',
                'id': str(uuid.uuid4()),
                'time': datetime.utcnow().isoformat(),
                'datacontenttype': 'application/json',
                'identifier': identifier,
                'data': {}
            }
            subject = APP_CONFIG.SUBSCRIPTION_OPTIONS['subject']
            publish_event(payload, subject)
        except Exception as err:  # pylint: disable=broad-except; # noqa: B902
            capture_message('Entity-bn queue publish identifier error: ' + identifier, level='error')
            logger.error('Queue Publish queue publish identifier error: %s %s', identifier, err, exc_info=True)
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
