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
"""Furnishings job."""
import asyncio
import logging
import os
import uuid
from datetime import datetime

import pytz
import requests
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from croniter import croniter
from flask import Flask, current_app
from legal_api.models import Batch, BatchProcessing, Business, Configuration, Furnishing, db  # noqa: I001
from legal_api.services.bootstrap import AccountService
from legal_api.services.flags import Flags
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService
from legal_api.services.queue import QueueService
from sentry_sdk.integrations.logging import LoggingIntegration

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
    db.init_app(app)

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


def get_email_address_from_auth(identifier: str):
    """Return email address from auth for notification, return None if it doesn't have one."""
    token = AccountService.get_bearer_token()
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    contact_info = requests.get(
        f'{current_app.config.get("AUTH_URL")}/entities/{identifier}',
        headers=headers
    )
    contacts = contact_info.json()['contacts']
    if not contacts or not contacts[0]['email']:
        return None
    return contacts[0]['email']


async def send_email(furnishing: Furnishing, app: Flask, qsm: QueueService):
    """Put email message on the queue for all email furnishing entries."""
    try:
        subject = app.config['NATS_EMAILER_SUBJECT']
        payload = {
            'specversion': '1.x-wip',
            'type': 'bc.registry.dissolution',
            'source': 'furnishingsJob',
            'id': str(uuid.uuid4()),
            'time': datetime.utcnow().isoformat(),
            'datacontenttype': 'application/json',
            'identifier': furnishing.business_identifier,
            'data': {
                'furnishing': {
                    'type': 'INVOLUNTARY_DISSOLUTION',
                    'furnishingId': furnishing.id,
                    'furnishingName': furnishing.furnishing_name.name
                }
            }
        }
        await qsm.publish_json_to_subject(payload, subject)
        app.logger.debug('Publish queue message %s: furnishing.id=%s', subject, furnishing.id)
    except Exception as err:
        app.logger.error('Queue Error: furnishing.id=%s, %s', furnishing.id, err, exc_info=True)


def create_new_furnishing(
        batch_processing: BatchProcessing,
        eligible_details: InvoluntaryDissolutionService.EligibilityDetails,
        furnishing_type: Furnishing.FurnishingType,
        grouping_identifier: int,
        email: str = None
        ):
    """Create new furnishing entry."""
    business = batch_processing.business
    if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value:
        furnishing_name = (
            Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO
            if eligible_details.transition_overdue
            else Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO
        )
    else:
        furnishing_name = (
            Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR
            if eligible_details.transition_overdue
            else Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR
        )

    new_furnishing = Furnishing(
        furnishing_type=furnishing_type,
        furnishing_name=furnishing_name,
        batch_id=batch_processing.batch_id,
        business_id=batch_processing.business_id,
        business_identifier=batch_processing.business_identifier,
        processed_date=datetime.utcnow(),
        created_date=datetime.utcnow(),
        last_modified=datetime.utcnow(),
        status=Furnishing.FurnishingStatus.QUEUED,
        grouping_identifier=grouping_identifier,
        email=email
    )
    new_furnishing.save()

    return new_furnishing


async def stage_1_process(app: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
    """Run process to manage and track notifications for dissolution stage 1 process."""
    try:  # pylint: disable=too-many-nested-blocks
        batch_processings = (
            db.session.query(BatchProcessing)
            .filter(BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING)
            .filter(BatchProcessing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1)
            .filter(Batch.id == BatchProcessing.batch_id)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(Batch.status == Batch.BatchStatus.PROCESSING)
        ).all()
        email_grouping_identifier = None
        for batch_processing in batch_processings:
            furnishings = Furnishing.find_by(
                batch_id=batch_processing.batch_id,
                business_id=batch_processing.business_id
                )
            if not furnishings:
                # send email/letter notification for the first time
                email = get_email_address_from_auth(batch_processing.business_identifier)
                if email:
                    # send email letter
                    _, eligible_details = InvoluntaryDissolutionService.check_business_eligibility(
                        batch_processing.business_identifier, False
                        )
                    if eligible_details:
                        if not email_grouping_identifier:
                            email_grouping_identifier = Furnishing.get_next_grouping_identifier()
                        new_furnishing = create_new_furnishing(
                            batch_processing,
                            eligible_details,
                            Furnishing.FurnishingType.EMAIL,
                            email_grouping_identifier,
                            email
                            )
                        # notify emailer
                        await send_email(new_furnishing, app, qsm)
                else:
                    # send paper letter if business doesn't have email address
                    pass
            else:
                # send paper letter if business is still not in good standing after 5 days of email letter sent out
                pass
    except Exception as err:
        app.logger.error(err)


def can_run_today(cron_value: str):
    """Check if cron string is valid for today."""
    tz = pytz.timezone('US/Pacific')
    today = tz.localize(datetime.today())
    result = croniter.match(cron_value, datetime(today.year, today.month, today.day))
    return result


def check_run_schedule():
    """Check if any of the dissolution stage is valid for this run."""
    stage_1_schedule_config = Configuration.find_by_name(
        config_name=Configuration.Names.DISSOLUTIONS_STAGE_1_SCHEDULE.value
    )
    stage_2_schedule_config = Configuration.find_by_name(
        config_name=Configuration.Names.DISSOLUTIONS_STAGE_2_SCHEDULE.value
    )
    stage_3_schedule_config = Configuration.find_by_name(
        config_name=Configuration.Names.DISSOLUTIONS_STAGE_3_SCHEDULE.value
    )

    cron_valid_1 = can_run_today(stage_1_schedule_config.val)
    cron_valid_2 = can_run_today(stage_2_schedule_config.val)
    cron_valid_3 = can_run_today(stage_3_schedule_config.val)

    return cron_valid_1, cron_valid_2, cron_valid_3


async def run(application: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
    """Run the stage 1-3 to manage and track notifications for dissolving businesses."""
    with application.app_context():
        flag_on = flags.is_on('enable-involuntary-dissolution')
        application.logger.debug(f'enable-involuntary-dissolution flag on: {flag_on}')
        if flag_on:
            # check if job can be run today
            stage_1_valid, stage_2_valid, stage_3_valid = check_run_schedule()
            application.logger.debug(
                f'Run schedule check: stage_1: {stage_1_valid}, stage_2: {stage_2_valid}, stage_3: {stage_3_valid}'
            )
            if not any([stage_1_valid, stage_2_valid, stage_3_valid]):
                application.logger.debug(
                    'Skipping job run since current day of the week does not match any cron schedule.'
                )
                return

            if stage_1_valid:
                await stage_1_process(application, qsm)
            if stage_2_valid:
                pass
            if stage_3_valid:
                pass


if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(run(application, queue_service))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
