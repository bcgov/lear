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
from entity_queue_common.service import QueueServiceManager
from entity_queue_common.service_utils import EmailException, QueueException, logger
from flask import Flask
from legal_api import db
from legal_api.models import Filing
from legal_api.services.bootstrap import AccountService
from legal_api.services.flags import Flags
from sqlalchemy.exc import OperationalError

from entity_digital_credentials import config


qsm = QueueServiceManager()  # pylint: disable=invalid-name
flags = Flags()  # pylint: disable=invalid-name
APP_CONFIG = config.get_named_config(os.getenv('DEPLOYMENT_ENV', 'production'))
FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(APP_CONFIG)
db.init_app(FLASK_APP)

if FLASK_APP.config.get('LD_SDK_KEY', None):
    flags.init_app(FLASK_APP)


def process_digital_credential(dc_msg: dict, flask_app: Flask):  # pylint: disable=too-many-branches, too-many-statements
    pass


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    with FLASK_APP.app_context():
        try:
            logger.info('Received raw message seq: %s, data=  %s',
                        msg.sequence, msg.data.decode())
            dc_msg = json.loads(msg.data.decode('utf-8'))
            logger.debug('Extracted digital credential msg: %s', dc_msg)
            process_digital_credential(dc_msg, FLASK_APP)
        except OperationalError as err:
            logger.error('Queue Blocked - Database Issue: %s',
                         json.dumps(dc_msg), exc_info=True)
            raise err  # We don't want to handle the error, as a DB down would drain the queue
        except (QueueException, Exception) as err:  # noqa B902; pylint: disable=W0703;
            # Catch Exception so that any error is still caught and the message is removed from the queue
            logger.error('Queue Error: %s', json.dumps(dc_msg), exc_info=True)
