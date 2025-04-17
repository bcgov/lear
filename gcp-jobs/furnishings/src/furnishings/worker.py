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
from datetime import datetime

import pytz
from croniter import croniter
from flask import current_app

from business_model.models import Configuration
from furnishings.services import post_processor, stage_one_processor, stage_three_process, stage_two_process
from furnishings.services.flags import Flags


def can_run_today(cron_value: str):
    """Check if cron string is valid for today."""
    tz = pytz.timezone("US/Pacific")
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


def run():
    """Run the stage 1-3 to manage and track notifications for dissolving businesses."""
    flag_on = Flags.is_on("enable-involuntary-dissolution")
    current_app.logger.debug(f"enable-involuntary-dissolution flag on: {flag_on}")
    if flag_on:
        # check if job can be run today
        stage_1_valid, stage_2_valid, stage_3_valid = check_run_schedule()
        current_app.logger.debug(
            f"Run schedule check: stage_1: {stage_1_valid}, stage_2: {stage_2_valid}, stage_3: {stage_3_valid}"
        )
        if not any([stage_1_valid, stage_2_valid, stage_3_valid]):
            current_app.logger.debug(
                "Skipping job run since current day of the week does not match any cron schedule."
            )
            return

        xml_furnishings_dict = {}

        if stage_1_valid:
            current_app.logger.debug("Entering stage 1 of furnishings job.")
            # NOTE: This stage is a two step process
            # 1. Send email (if available), completion dependent on business-emailer updating status
            # 2. Send mail (will only happen after step 1 is completed)
            stage_one_processor.process()
            current_app.logger.debug("Exiting stage 1 of furnishings job.")
        if stage_2_valid:
            current_app.logger.debug("Entering stage 2 of furnishings job.")
            # NOTE: Entering this stage is dependent on Involuntary Dissolution job updating the BatchProcessing.step
            stage_two_process(xml_furnishings_dict)
            current_app.logger.debug("Exiting stage 2 of furnishings job.")
        if stage_3_valid:
            current_app.logger.debug("Entering stage 3 of furnishings job.")
            stage_three_process(xml_furnishings_dict)
            current_app.logger.debug("Exiting stage 3 of furnishings job.")

        current_app.logger.debug("Entering post processing for the furnishings job.")
        post_processor.post_process(xml_furnishings_dict)
        current_app.logger.debug("Exiting post processing for the furnishings job.")
