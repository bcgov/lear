# Copyright © 2023 Province of British Columbia
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
from enum import Enum

import nats
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import QueueException, logger
from flask import Flask
from legal_api import init_db
from legal_api.core import Filing as FilingCore
from legal_api.models import Business
from legal_api.services import digital_credentials, flags
from sqlalchemy.exc import OperationalError

from entity_digital_credentials import config
from entity_digital_credentials.digital_credentials_processors import (
    admin_revoke,
    business_number,
    change_of_registration,
    dissolution,
    put_back_on,
)


qsm = QueueServiceManager()  # pylint: disable=invalid-name

APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
init_db(FLASK_APP)

with FLASK_APP.app_context():  # db require app context
    digital_credentials.init_app(FLASK_APP)

if FLASK_APP.config.get('LD_SDK_KEY', None):
    flags.init_app(FLASK_APP)


class AdminMessage(Enum):
    """Entity Digital Credential admin message type."""

    REVOKE = 'bc.registry.admin.revoke'


class BusinessMessage(Enum):
    """Entity Digital Credential business message type."""

    BN = 'bc.registry.business.bn'
    CHANGE_OF_REGISTRATION = f'bc.registry.business.{FilingCore.FilingTypes.CHANGEOFREGISTRATION.value}'
    DISSOLUTION = f'bc.registry.business.{FilingCore.FilingTypes.DISSOLUTION.value}'
    PUT_BACK_ON = f'bc.registry.business.{FilingCore.FilingTypes.PUTBACKON.value}'


async def process_digital_credential(dc_msg: dict, flask_app: Flask):
    # pylint: disable=too-many-branches, too-many-statements
    """Process any digital credential messages in queue."""
    if not dc_msg or dc_msg.get('type') not in [
            BusinessMessage.CHANGE_OF_REGISTRATION.value,
            BusinessMessage.DISSOLUTION.value,
            BusinessMessage.PUT_BACK_ON.value,
            BusinessMessage.BN.value,
            AdminMessage.REVOKE.value
    ]:
        return None

    if not flask_app:
        raise QueueException('Flask App not available.')

    with flask_app.app_context():
        logger.debug('Attempting to process digital credential message: %s', dc_msg)

        if dc_msg['type'] in (BusinessMessage.BN.value, AdminMessage.REVOKE.value):
            # When a BN is added or changed or there is a manuak administrative update the queue message does not have
            # a data object. We queue the business information using the identifier and revoke/reissue the credential
            # immediately.
            if dc_msg.get('identifier') is None:
                raise QueueException('Digital credential message is missing identifier')

            identifier = dc_msg['identifier']
            if not (business := Business.find_by_identifier(identifier)):  # pylint: disable=superfluous-parens
                # pylint: disable=broad-exception-raised
                raise Exception(f'Business with identifier: {identifier} not found.')

            if dc_msg['type'] == BusinessMessage.BN.value:
                await business_number.process(business)
            elif dc_msg['type'] == AdminMessage.REVOKE.value:
                await admin_revoke.process(business)
        else:
            if dc_msg.get('data') is None \
                    or dc_msg.get('data').get('filing') is None \
                    or dc_msg.get('data').get('filing').get('header') is None \
                    or dc_msg.get('data').get('filing').get('header').get('filingId') is None:
                raise QueueException('Digital credential message is missing data.')

            filing_id = dc_msg['data']['filing']['header']['filingId']

            if not (filing_core := FilingCore.find_by_id(filing_id)):  # pylint: disable=superfluous-parens
                raise QueueException(f'Filing not found for id: {filing_id}.')

            if not (filing := filing_core.storage):  # pylint: disable=superfluous-parens
                raise QueueException(f'Filing not found for id: {filing_id}.')

            if filing.status != FilingCore.Status.COMPLETED.value:
                raise QueueException(f'Filing with id: {filing_id} processing not complete.')

            business_id = filing.business_id
            if not (business := Business.find_by_internal_id(business_id)):  # pylint: disable=superfluous-parens
                # pylint: disable=broad-exception-raised
                raise Exception(f'Business with internal id: {business_id} not found.')

            # Process individual filing events
            if filing.filing_type == FilingCore.FilingTypes.CHANGEOFREGISTRATION.value:
                await change_of_registration.process(business, filing)
            if filing.filing_type == FilingCore.FilingTypes.DISSOLUTION.value:
                filing_sub_type = filing.filing_sub_type
                await dissolution.process(business, filing_sub_type)  # pylint: disable=too-many-function-args
            if filing.filing_type == FilingCore.FilingTypes.PUTBACKON.value:
                await put_back_on.process(business)


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    with FLASK_APP.app_context():
        try:
            logger.info('Received raw message seq: %s, data=  %s',
                        msg.sequence, msg.data.decode())
            dc_msg = json.loads(msg.data.decode('utf-8'))
            logger.debug('Extracted digital credential msg: %s', dc_msg)
            await process_digital_credential(dc_msg, FLASK_APP)
        except OperationalError as err:
            logger.error('Queue Blocked - Database Issue: %s',
                         json.dumps(dc_msg), exc_info=True)
            raise err  # We don't want to handle the error, as a DB down would drain the queue
        except (QueueException, Exception) as err:  # noqa B902; pylint: disable=W0703, disable=unused-variable
            # Catch Exception so that any error is still caught and the message is removed from the queue
            logger.error('Queue Error: %s', json.dumps(dc_msg), exc_info=True)
