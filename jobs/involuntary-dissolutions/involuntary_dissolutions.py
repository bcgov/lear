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
"""Involuntary dissolutions job."""
import asyncio
import logging
import os
from datetime import datetime, timedelta

import pytz
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from croniter import croniter
from flask import Flask
from legal_api.core.filing import Filing as CoreFiling
from legal_api.models import Batch, BatchProcessing, Business, Configuration, Filing, db  # noqa: I001
from legal_api.services.filings.validations.dissolution import DissolutionTypes
from legal_api.services.flags import Flags
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService
from legal_api.services.queue import QueueService
from sentry_sdk import capture_message
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import aliased

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


def create_invountary_dissolution_filing(business_id: int):
    """Create a filing entry to represent an involuntary dissolution filing."""
    business = Business.find_by_internal_id(business_id)

    filing = Filing()
    filing.business_id = business.id
    filing._filing_type = CoreFiling.FilingTypes.DISSOLUTION  # pylint: disable=protected-access
    filing._filing_sub_type = DissolutionTypes.INVOLUNTARY  # pylint: disable=protected-access
    filing.filing_json = {
        'filing': {
            'header': {
                'date': datetime.utcnow().date().isoformat(),
                'name': 'dissolution',
                'certifiedBy': ''
            },
            'business': {
                'legalName': business.legal_name,
                'legalType': business.legal_type,
                'identifier': business.identifier,
                'foundingDate': business.founding_date.isoformat()
            },
            'dissolution': {
                'dissolutionDate': datetime.utcnow().date().isoformat(),
                'dissolutionType': 'involuntary'
            }
        }
    }

    filing.save()

    return filing


async def put_filing_on_queue(filing_id: int, app: Flask, qsm: QueueService):
    """Send queue message to filer to dissolve business."""
    try:
        subject = app.config['NATS_FILER_SUBJECT']
        payload = {'filing': {'id': filing_id}}
        await qsm.publish_json_to_subject(payload, subject)
    except Exception as err:  # pylint: disable=broad-except # noqa F841;
        # mark any failure for human review
        capture_message(
            f'Queue Error: Failed to place filing {filing_id} on Queue with error:{err}',
            level='error'
        )


def mark_eligible_batches_completed():
    """Mark batches completed if all of their associated batch_processings are compeleted."""
    AliasBatchProcessing = aliased(BatchProcessing)  # pylint: disable=invalid-name # noqa N806
    batches = (
        db.session.query(Batch)
        .join(BatchProcessing, Batch.id == BatchProcessing.batch_id)
        .filter(Batch.batch_type == 'INVOLUNTARY_DISSOLUTION')
        .filter(Batch.status != 'COMPLETED')
        .filter(
            ~db.session.query(AliasBatchProcessing)
            .filter(Batch.id == AliasBatchProcessing.batch_id)
            .filter(AliasBatchProcessing.status.notin_(['COMPLETED', 'WITHDRAWN']))
            .exists()
        )
        .all()
    )

    for batch in batches:
        batch.status = Batch.BatchStatus.COMPLETED
        batch.end_date = datetime.utcnow()
        batch.save()


def stage_1_process(app: Flask):  # pylint: disable=redefined-outer-name,too-many-locals
    """Initiate dissolution process for new businesses that meet dissolution criteria."""
    try:
        # check if batch has already run today
        today_date = datetime.utcnow().date()

        batch_today = (
            db.session.query(Batch)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(cast(Batch.start_date, Date) == today_date)
        ).all()

        if len(batch_today) > 0:
            app.logger.debug('Skipping job run since batch job has already run today.')
            return

        # get first NUM_DISSOLUTIONS_ALLOWED number of businesses
        num_dissolutions_allowed = Configuration.find_by_name(config_name='NUM_DISSOLUTIONS_ALLOWED').val
        businesses_eligible = InvoluntaryDissolutionService.get_businesses_eligible(num_dissolutions_allowed)

        if len(businesses_eligible) == 0:
            app.logger.debug('Skipping job run since there are no businesses eligible for dissolution.')
            return

        # get stage_1 & stage_2 delay configs
        stage_1_delay = timedelta(days=app.config.get('STAGE_1_DELAY'))
        stage_2_delay = timedelta(days=app.config.get('STAGE_2_DELAY'))

        # create new entry in batches table
        batch = Batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                      status=Batch.BatchStatus.PROCESSING,
                      size=len(businesses_eligible),
                      start_date=datetime.utcnow())
        batch.save()

        # create batch processing entries for each business being dissolved
        for business_elgible in businesses_eligible:
            business, ar_overdue, transition_overdue = business_elgible
            batch_processing = BatchProcessing(business_identifier=business.identifier,
                                               step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                                               status=BatchProcessing.BatchProcessingStatus.PROCESSING,
                                               created_date=datetime.utcnow(),
                                               trigger_date=datetime.utcnow()+stage_1_delay,
                                               batch_id=batch.id,
                                               business_id=business.id)

            target_dissolution_date = batch_processing.created_date + stage_1_delay + stage_2_delay

            batch_processing.meta_data = {
                'overdueARs': ar_overdue,
                'overdueTransition': transition_overdue,
                'targetDissolutionDate': target_dissolution_date.date().isoformat()
            }
            batch_processing.save()

    except Exception as err:  # pylint: disable=redefined-outer-name; noqa: B902
        app.logger.error(err)


def stage_2_process(app: Flask):
    """Update batch processing data for previously created in_progress batches."""
    batch_processings = (
        db.session.query(BatchProcessing)
        .filter(BatchProcessing.batch_id == Batch.id)
        .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
        .filter(Batch.status == Batch.BatchStatus.PROCESSING)
        .filter(
            BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING
        )
        .filter(
            BatchProcessing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1
        )
        .filter(
            BatchProcessing.trigger_date <= func.timezone('UTC', func.now())
        )
        .all()
    )

    # TODO: add check if warnings have been sent out & set batch_processing.status to error if not

    stage_2_delay = timedelta(days=app.config.get('STAGE_2_DELAY'))

    for batch_processing in batch_processings:
        eligible, _ = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier, exclude_in_dissolution=False
        )
        if eligible:
            batch_processing.step = BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
            batch_processing.trigger_date = datetime.utcnow() + stage_2_delay
        else:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN
            batch_processing.notes = 'Moved back into good standing'
        batch_processing.last_modified = datetime.utcnow()
        batch_processing.save()


async def stage_3_process(app: Flask, qsm: QueueService):
    """Process actual dissolution of businesses."""
    batch_processings = (
        db.session.query(BatchProcessing)
        .filter(BatchProcessing.batch_id == Batch.id)
        .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
        .filter(Batch.status == Batch.BatchStatus.PROCESSING)
        .filter(
            BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING
        )
        .filter(
            BatchProcessing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        )
        .filter(
            BatchProcessing.trigger_date <= func.timezone('UTC', func.now())
        )
        .all()
    )

    # TODO: add check if warnings have been sent out & set batch_processing.status to error if not

    for batch_processing in batch_processings:
        eligible, _ = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier, exclude_in_dissolution=False
        )
        if eligible:
            filing = create_invountary_dissolution_filing(batch_processing.business_id)
            await put_filing_on_queue(filing.id, app, qsm)

            batch_processing.step = BatchProcessing.BatchProcessingStep.DISSOLUTION
            batch_processing.status = BatchProcessing.BatchProcessingStatus.COMPLETED
        else:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN
            batch_processing.notes = 'Moved back into good standing'
        batch_processing.last_modified = datetime.utcnow()
        batch_processing.save()

    mark_eligible_batches_completed()


def can_run_today(cron_value: str):
    """Check if cron string is valid for today."""
    tz = pytz.timezone('US/Pacific')
    today = tz.localize(datetime.today())
    result = croniter.match(cron_value, datetime(today.year, today.month, today.day))
    return result


def check_run_schedule():
    """Check if any of the dissolution stages are valid for this run."""
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
    """Run the stage 1-3 methods for dissolving businesses."""
    if application is None:
        application = create_app()

    with application.app_context():
        flag_on = flags.is_on('enable-involuntary-dissolution')
        application.logger.debug(f'enable-involuntary-dissolution flag on: {flag_on}')
        if flag_on:
            # check if batch can be run today
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
                stage_1_process(application)
            if stage_2_valid:
                stage_2_process(application)
            if stage_3_valid:
                await stage_3_process(application, qsm)


if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        queue_service = QueueService(app=application, loop=event_loop)
        event_loop.run_until_complete(run(application, queue_service))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
