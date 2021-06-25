# Copyright © 2021 Province of British Columbia
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
"""Email reminder."""
import asyncio
import logging
import os

import requests
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from legal_api.models import Business, Filing, db  # noqa: I001
from legal_api.services.bootstrap import AccountService
from legal_api.services.queue import QueueService
from sentry_sdk import capture_message
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlalchemy.sql.expression import text  # noqa: I001

import config  # pylint: disable=import-error
from utils.logging import setup_logging  # pylint: disable=import-error

# noqa: I003

setup_logging(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])
    db.init_app(app)

    # Configure Sentry
    if app.config.get('SENTRY_DSN', None):
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[SENTRY_LOGGING]
        )

    register_shellcontext(app)

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {'app': app}

    app.shell_context_processor(shell_context)


async def send_email(business_id: int, ar_fee: str, ar_year: str, app: Flask, qsm: QueueService):
    """Put bn email messages on the queue for all businesses with new tax ids."""
    try:
        subject = app.config['NATS_EMAILER_SUBJECT']
        payload = {
            'email': {
                'businessId': business_id,
                'type': 'annualReport',
                'option': 'reminder',
                'arFee': ar_fee,
                'arYear': ar_year
            }
        }
        await qsm.publish_json_to_subject(payload, subject)
    except Exception as err:  # pylint: disable=broad-except # noqa F841;
        # mark any failure for human review
        capture_message(
            f'Queue Error: Failed to place ar reminder email for business id {business_id} on Queue with error:{err}',
            level='error'
        )


def get_ar_fee(app: Flask, legal_type: str, token: str) -> str:
    """Get AR fee."""
    fee_url = app.config.get('PAYMENT_SVC_URL')
    filing_type_code = Filing.FILINGS['annualReport']['codes'].get(legal_type, None)
    fee_url = ''.join([fee_url, '/', legal_type, '/', filing_type_code])
    res = requests.get(url=fee_url,
                       headers={
                           'Content-Type': 'application/json',
                           'Authorization': 'Bearer ' + token})

    ar_fee = res.json().get('filingFees')
    return str(ar_fee)


def get_businesses(legal_types: list):
    """Get businesses to send AR reminder today."""
    where_clause = text(
        'CASE WHEN last_ar_year IS NULL' +
        " THEN date(founding_date) + interval '1 year' ELSE" +
        ' date(founding_date) + MAKE_INTERVAL(YEARS := last_ar_year - EXTRACT(YEAR FROM founding_date)::INTEGER)' +
        # ' END = CURRENT_DATE')
        " END = '2021-11-02'")
    return db.session.query(Business).filter(
        Business.legal_type.in_(legal_types), where_clause
    ).all()


async def find_and_send_ar_reminder(app: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
    """Find business to send annual report reminder."""
    try:
        legal_types = [Business.LegalTypes.BCOMP.value]  # entity types to send ar reminder
        ar_fees = {}

        # get token
        token = AccountService.get_bearer_token()
        for legal_type in legal_types:
            ar_fees[legal_type] = get_ar_fee(app, legal_type, token)

        app.logger.debug('Getting businesses to send AR reminder today')
        businesses = get_businesses(legal_types)
        app.logger.debug('Processing businesses to send AR reminder')
        for business in businesses:
            ar_year = (business.last_ar_year if business.last_ar_year else business.founding_date.year) + 1

            await send_email(business.id, ar_fees[business.legal_type], str(ar_year), app, qsm)
            app.logger.debug(f'Successfully queued ar reminder for business id {business.id}.')

    except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
        app.logger.error(err)


if __name__ == '__main__':
    application = create_app()
    with application.app_context():
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(find_and_send_ar_reminder(application, queue_service))
