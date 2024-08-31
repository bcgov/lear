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
"""Furnishings job worker functionality is contained here."""
import logging
import os
from datetime import datetime

import pytz
import sentry_sdk  # noqa: I001, E501; pylint: disable=ungrouped-imports; conflicts with Flake8
from croniter import croniter
from flask import Flask
from legal_api.models import Configuration, db
from legal_api.services.flags import Flags
from legal_api.services.queue import QueueService
from sentry_sdk.integrations.logging import LoggingIntegration

from furnishings.config import get_named_config  # pylint: disable=import-error
from furnishings.stage_processors import post_processor, stage_one, stage_three, stage_two
from furnishings.utils.logging import setup_logging  # pylint: disable=import-error


setup_logging(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logging.conf'))

SENTRY_LOGGING = LoggingIntegration(
    event_level=logging.ERROR  # send errors as events
)

flags = Flags()


def create_app(run_mode=os.getenv('FLASK_ENV', 'production')):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(get_named_config(run_mode))
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

            xml_furnishings_dict = {}

            if stage_1_valid:
                application.logger.debug('Entering stage 1 of furnishings job.')
                await stage_one.process(application, qsm)
                application.logger.debug('Exiting stage 1 of furnishings job.')
            if stage_2_valid:
                application.logger.debug('Entering stage 2 of furnishings job.')
                stage_two.process(application, xml_furnishings_dict)
                application.logger.debug('Exiting stage 2 of furnishings job.')
            if stage_3_valid:
                application.logger.debug('Entering stage 3 of furnishings job.')
                stage_three.process(application, xml_furnishings_dict)
                application.logger.debug('Exiting stage 3 of furnishings job.')

            application.logger.debug('Entering post processing for the furnishings job.')
            post_processor.process(application, xml_furnishings_dict)
            application.logger.debug('Exiting post processing for the furnishings job.')
