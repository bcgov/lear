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
"""Email Reminder job."""
import asyncio
import logging
import os
import sys

import requests
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from flask import Flask
from legal_api import init_db
from legal_api.models import Business, Filing, db # noqa: I001
from legal_api.services.bootstrap import AccountService
from legal_api.services.flags import Flags
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

flags = Flags()


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(config.CONFIGURATION[run_mode])
    init_db(app)

    # Configure Sentry
    if app.config.get('SENTRY_DSN', None):
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[SENTRY_LOGGING]
        )

    if app.config.get('LD_SDK_KEY', None):
        flags.init_app(app)

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
    app.logger.debug(f'token: {token}')
    app.logger.debug(f'legal_type: {legal_type}')
    fee_url = app.config.get('PAYMENT_SVC_FEES_URL')
    app.logger.debug(f'fee_url: {fee_url}')
    filing_type_code = Filing.FILINGS['annualReport']['codes'].get(legal_type, None)
    ar_filing = Filing.FILINGS['annualReport']
    app.logger.debug(f'Filing.FILINGS: {ar_filing}')
    app.logger.debug(f'filing_type_code: {filing_type_code}')
    fee_url = ''.join([fee_url, '/', legal_type, '/', filing_type_code])
    app.logger.debug(f'fee_url: {fee_url}')
    res = requests.get(url=fee_url,  # pylint: disable=missing-timeout
                       headers={
                           'Content-Type': 'application/json',
                           'Authorization': 'Bearer ' + token})
    app.logger.debug(f'res: {res}')
    app.logger.debug(f'res: {res.json()}')
    ar_fee = res.json().get('filingFees')
    app.logger.debug(f'ar_fee: {ar_fee}')
    return str(ar_fee)


def get_businesses(legal_types: list):
    """Get businesses to send AR reminder today."""
    where_clause = text(
        'CASE WHEN last_ar_reminder_year IS NULL THEN date(founding_date)' +
        ' ELSE date(founding_date)' +
        ' + MAKE_INTERVAL(YEARS := last_ar_reminder_year - EXTRACT(YEAR FROM founding_date)::INTEGER)' +
        " END  + interval '1 year' <= CURRENT_DATE")
    return db.session.query(Business).filter(
        Business.legal_type.in_(legal_types),
        Business.send_ar_ind == True,  # pylint: disable=singleton-comparison; # noqa: E712;
        Business.state == Business.State.ACTIVE,
        # restoration_expiry_date will have a value for limitedRestoration and limitedRestorationExtension
        Business.restoration_expiry_date == None,  # pylint: disable=singleton-comparison; # noqa: E711;
        where_clause
    ).order_by(Business.id).paginate(per_page=20)


async def find_and_send_ar_reminder(app: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
    """Find business to send annual report reminder."""
    try:
        legal_types = [Business.LegalTypes.BCOMP.value,
                       Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                       Business.LegalTypes.CONTINUE_IN.value,
                       Business.LegalTypes.ULC_CONTINUE_IN.value,
                       Business.LegalTypes.CCC_CONTINUE_IN.value,]  # entity types to send ar reminder

        if flags.is_on('enable-bc-ccc-ulc'):
            legal_types.extend(
                [Business.LegalTypes.COMP.value,
                 Business.LegalTypes.BC_CCC.value,
                 Business.LegalTypes.BC_ULC_COMPANY.value]
            )

        ar_fees = {}

        # get token
        token = AccountService.get_bearer_token()
        for legal_type in legal_types:
            ar_fees[legal_type] = get_ar_fee(app, legal_type, token)

        app.logger.debug('Getting businesses to send AR reminder today')
        pagination = get_businesses(legal_types)
        while pagination.items:
            app.logger.debug('Processing businesses to send AR reminder')
            for business in pagination.items:
                ar_year = (business.last_ar_reminder_year
                           if business.last_ar_reminder_year else business.founding_date.year) + 1

                await send_email(business.id, ar_fees[business.legal_type], str(ar_year), app, qsm)
                app.logger.debug(f'Successfully queued ar reminder for business id {business.id}.')
                business.last_ar_reminder_year = ar_year
                business.save()

            if pagination.next_num:
                pagination = pagination.next()
            else:
                break

    except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
        app.logger.error(err)


async def send_outstanding_bcomps_ar_reminder(app: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
    """Find outstanding bcomps to send annual report reminder."""
    try:
        # get token
        token = AccountService.get_bearer_token()
        ar_fee = get_ar_fee(app, Business.LegalTypes.BCOMP.value, token)

        app.logger.debug('Getting outstanding bcomps to send AR reminder')
        where_clause = text(
            'CASE WHEN last_ar_date IS NULL THEN date(founding_date) ELSE date(last_ar_date) END' +
            " <= CURRENT_DATE - interval '1 year'")
        businesses = db.session.query(Business).filter(
            Business.legal_type == Business.LegalTypes.BCOMP.value,
            where_clause
        ).all()
        app.logger.debug('Processing outstanding bcomps to send AR reminder')

        for business in businesses:
            ar_year = (business.last_ar_year if business.last_ar_year else business.founding_date.year) + 1

            await send_email(business.id, ar_fee, str(ar_year), app, qsm)
            app.logger.debug(f'Successfully queued ar reminder for business id {business.id} for year {ar_year}.')

    except Exception as err:  # pylint: disable=broad-except, unused-variable # noqa F841;
        app.logger.error(err)


if __name__ == '__main__':
    condition = sys.argv[1] if sys.argv and len(sys.argv) > 1 else None  # pylint: disable=invalid-name
    application = create_app()
    with application.app_context():
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        send_outstanding_bcomps = application.config.get('SEND_OUTSTANDING_BCOMPS')
        if condition == 'outstanding-bcomps' or send_outstanding_bcomps == 'send.outstanding.bcomps':
            event_loop.run_until_complete(send_outstanding_bcomps_ar_reminder(application, queue_service))
        else:
            event_loop.run_until_complete(find_and_send_ar_reminder(application, queue_service))
