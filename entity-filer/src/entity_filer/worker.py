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
import datetime
import json

import nats
from flask import Flask
from legal_api import db
from legal_api.models import Business, Filing
from sqlalchemy_continuum import versioning_manager

from entity_filer.config import get_named_config
from entity_filer.filing_processors import annual_report, change_of_address
from entity_filer.service_utils import logger


def extract_payment_token(msg: nats.aio.client.Msg) -> dict:
    """Return a dict of the json string in the Msg.data."""
    return json.loads(msg.data.decode('utf-8'))


def get_filing_by_payment_id(payment_id: int) -> Filing:
    """Return the outcome of Filing.get_filing_by_payment_token."""
    return Filing.get_filing_by_payment_token(str(payment_id))


def process_filing(payment_token, flask_app):
    """Render the filings contained in the submission."""
    if not flask_app:
        raise Exception

    with flask_app.app_context():
        filing_submission = get_filing_by_payment_id(payment_token['paymentToken'].get('id'))
        legal_filings = filing_submission.legal_filings()
        # TODO: handle case where there are no legal_filings

        uow = versioning_manager.unit_of_work(db.session)
        transaction = uow.create_transaction(db.session)

        if not payment_token['paymentToken'].get('statusCode') == 'TRANSACTION_FAILED':
            if not payment_token['paymentToken'].get('statusCode') == Filing.Status.COMPLETED.value:
                logger.error('Unknown payment status given: %s', payment_token['paymentToken'].get('statusCode'))
                raise Exception

            business = Business.find_by_internal_id(filing_submission.business_id)

            for filing in legal_filings:
                if filing.get('annualReport'):
                    annual_report.process(business, filing, filing_submission.filing_date)
                if filing.get('changeOfAddress'):
                    change_of_address.process(business, filing)

            filing_submission.transaction_id = transaction.id

        filing_submission.payment_completion_date = datetime.datetime.utcnow()
        filing_submission.save()


FLASK_APP = Flask(__name__)
FLASK_APP.config.from_object(get_named_config('production'))
db.init_app(FLASK_APP)


async def cb_subscription_handler(msg: nats.aio.client.Msg):
    """Use Callback to process Queue Msg objects."""
    logger.info('Received raw message seq:%s, data=  %s', msg.sequence, msg.data.decode())
    payment_token = extract_payment_token(msg)
    logger.debug('Extracted payment token: %s', payment_token)
    process_filing(payment_token, FLASK_APP)
