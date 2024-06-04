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
from legal_api.models import Batch, BatchProcessing, Configuration, db  # noqa: I001
from legal_api.services.flags import Flags
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlalchemy import Date, cast, func, text

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


def initiate_dissolution_process(app: Flask):  # pylint: disable=redefined-outer-name,too-many-locals
    """Initiate dissolution process for new businesses that meet dissolution criteria."""
    try:
        # check if batch has already run today
        tz = pytz.timezone('US/Pacific')
        today_date = tz.localize(datetime.today()).date()

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

        # create new entry in batches table
        batch = Batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                      status=Batch.BatchStatus.PROCESSING,
                      size=len(businesses_eligible),
                      start_date=datetime.now())
        batch.save()

        # create batch processing entries for each business being dissolved
        for business_elgible in businesses_eligible:
            business, ar_overdue, transition_overdue = business_elgible
            batch_processing = BatchProcessing(business_identifier=business.identifier,
                                               step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                                               status=BatchProcessing.BatchProcessingStatus.PROCESSING,
                                               created_date=datetime.now(),
                                               batch_id=batch.id,
                                               business_id=business.id)

            if (stage_1_delay_config := app.config.get('STAGE_1_DELAY', 0)):
                stage_1_delay = timedelta(days=int(stage_1_delay_config))
            else:
                stage_1_delay = timedelta(days=0)

            if (stage_2_delay_config := app.config.get('STAGE_2_DELAY', 0)):
                stage_2_delay = timedelta(days=int(stage_2_delay_config))
            else:
                stage_2_delay = timedelta(days=0)

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
    """Run dissolution stage 2 process for businesses meet moving criteria."""
    if not (stage_2_delay := app.config.get('STAGE_2_DELAY', None)):
        app.logger.debug('Skipping stage 2 run since config STAGE_2_DELAY is missing.')
        return

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
            BatchProcessing.created_date + text(f"""INTERVAL '{stage_2_delay} DAYS'""")
            <= func.timezone('UTC', func.now())
        )
        .all()
    )

    # TODO: add check if warnings have been sent out & set batch_processing.status to error if not

    for batch_processing in batch_processings:
        eligible, _ = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier, exclude_in_dissolution=False
        )
        if eligible:
            batch_processing.step = BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        else:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN

            batch_processing.notes = (
                batch_processing.notes + ', ' if batch_processing.notes else ''
            )
            batch_processing.notes += 'Moved back into good standing'
        batch_processing.last_modified = datetime.utcnow()
        batch_processing.save()


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
    tz = pytz.timezone('US/Pacific')
    today = tz.localize(datetime.today())
    cron_valid_1 = croniter.match(stage_1_schedule_config.val, today)
    cron_valid_2 = croniter.match(stage_2_schedule_config.val, today)
    cron_valid_3 = croniter.match(stage_3_schedule_config.val, today)

    return cron_valid_1, cron_valid_2, cron_valid_3


async def run(loop, application: Flask = None):  # pylint: disable=redefined-outer-name
    """Run the stage 1-3 methods for dissolving businesses."""
    if application is None:
        application = create_app()

    with application.app_context():
        flag_on = flags.is_on('enable-involuntary-dissolution')
        application.logger.debug(f'enable-involuntary-dissolution flag on: {flag_on}')
        if flag_on:
            # check if batch can be run today
            cron_valids = check_run_schedule()
            if not any(cron_valids):
                application.logger.debug('Skipping job run since current day of the week does not match any cron schedule.')  # noqa: E501
                return

            if cron_valids[0]:
                initiate_dissolution_process(application)
            if cron_valids[1]:
                stage_2_process(application)
            if cron_valids[2]:
                pass


if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop, application))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
