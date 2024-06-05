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


def initiate_dissolution_process(app: Flask):  # pylint: disable=redefined-outer-name
    """Initiate dissolution process for new businesses that meet dissolution criteria."""
    try:
        # check if batch has already run today
        batch_today = (
            db.session.query(Batch)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(Batch.start_date + timedelta(days=1) > datetime.now())
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

            stage_1_delay = timedelta(days=app.config.get('STAGE_1_DELAY', 0))
            stage_2_delay = timedelta(days=app.config.get('STAGE_2_DELAY', 0))
            target_dissolution_date = batch_processing.created_date + stage_1_delay + stage_2_delay

            batch_processing.meta_data = {
                'overdueARs': ar_overdue,
                'overdueTransition': transition_overdue,
                'targetDissolutionDate': target_dissolution_date.date().isoformat()
            }
            batch_processing.save()

    except Exception as err:  # pylint: disable=redefined-outer-name; noqa: B902
        app.logger.error(err)


async def run(loop, application: Flask = None):  # pylint: disable=redefined-outer-name
    """Run the stage 1-3 methods for dissolving businesses."""
    if application is None:
        application = create_app()

    with application.app_context():
        flag_on = flags.is_on('enable-involuntary-dissolution')
        application.logger.debug(f'enable-involuntary-dissolution flag on: {flag_on}')
        if flag_on:
            # check if batch can be run today
            new_dissolutions_schedule_config = Configuration.find_by_name(config_name='DISSOLUTIONS_STAGE_1_SCHEDULE')
            tz = pytz.timezone('US/Pacific')
            cron_valid = croniter.match(new_dissolutions_schedule_config.val, tz.localize(datetime.today()))
            if cron_valid:
                initiate_dissolution_process(application)
            else:
                application.logger.debug('Skipping job run since current day of the week does not match the cron schedule.')  # noqa: E501

if __name__ == '__main__':
    application = create_app()
    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(run(event_loop, application))
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
