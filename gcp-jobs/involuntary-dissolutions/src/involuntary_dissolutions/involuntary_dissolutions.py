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
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytz
from croniter import croniter
from flask import Flask
from simple_cloudevent import SimpleCloudEvent, to_queue_message
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import aliased

from business_common.core.filing import Filing as CoreFiling
from business_model.models import (
    Batch,
    BatchProcessing,
    Business,
    Configuration,
    Filing,
    Furnishing,
    db,
)
from business_model.models.db import init_db
from dissolution_service import InvoluntaryDissolutionService
from gcp_queue import GcpQueue
from structured_logging import StructuredLogging

try:
    from config.config import get_named_config
    from utils.flags import Flags
    from utils.involuntary_dissolution_types import DissolutionTypes
except ImportError:
    from involuntary_dissolutions.config.config import get_named_config
    from involuntary_dissolutions.utils.flags import Flags
    from involuntary_dissolutions.utils.involuntary_dissolution_types import DissolutionTypes

gcp_queue = GcpQueue()

flags = Flags()

env = os.getenv("DEPLOYMENT_ENV", "production")
def create_app(run_mode=env):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config.from_object(get_named_config(run_mode))
    app.env = run_mode
    init_db(app)

    if app.config.get("LD_SDK_KEY", None):
        flags.init_app(app)

    register_shellcontext(app)
    gcp_queue.init_app(app)
    app.logger = StructuredLogging(app).get_logger()

    return app


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {"app": app}

    app.shell_context_processor(shell_context)


def create_invountary_dissolution_filing(business_id: int):
    """Create a filing entry to represent an involuntary dissolution filing."""
    business = Business.find_by_internal_id(business_id)

    filing = Filing()
    filing.business_id = business.id
    filing._filing_type = CoreFiling.FilingTypes.DISSOLUTION  # pylint: disable=protected-access
    filing._filing_sub_type = DissolutionTypes.INVOLUNTARY  # pylint: disable=protected-access
    filing.filing_json = {
        "filing": {
            "header": {
                "date": datetime.now(UTC).date().isoformat(),
                "name": "dissolution",
                "certifiedBy": ""
            },
            "business": {
                "legalName": business.legal_name,
                "legalType": business.legal_type,
                "identifier": business.identifier,
                "foundingDate": business.founding_date.isoformat()
            },
            "dissolution": {
                "dissolutionDate": datetime.now(UTC).date().isoformat(),
                "dissolutionType": "involuntary"
            }
        }
    }

    filing.hide_in_ledger = True
    filing.save()

    return filing


def put_filing_on_queue(filing_id: int, app: Flask):
    """Send queue message to filer to dissolve business."""
    try:
        subject = app.config["BUSINESS_FILER_TOPIC"]
        msg = {"filingMessage": {"filingIdentifier": filing_id}}
        app.logger.debug(f"Attempting to place filing on Filer Queue with id {filing_id}")
        ce = SimpleCloudEvent(
            id=str(uuid.uuid4()),
            source=app.config.get("CLIENT_NAME"),
            type="filingMessage",
            time=datetime.now(UTC),
            data = msg
        )
        gcp_queue.publish(subject, to_queue_message(ce))
        app.logger.debug(f"Successfully placed filing on Filer Queue with id {filing_id}")
    except Exception as err:  # pylint: disable=broad-except
        # mark any failure for human review
        app.logger.error(
            f"Queue Error: Failed to place filing {filing_id} on Queue with error:{err}"
        )


def mark_eligible_batches_completed():
    """Mark batches completed if all of their associated batch_processings are completed."""
    AliasBatchProcessing = aliased(BatchProcessing)  # pylint: disable=invalid-name # noqa: N806
    batches = (
        db.session.query(Batch)
        .join(BatchProcessing, Batch.id == BatchProcessing.batch_id)
        .filter(Batch.batch_type == "INVOLUNTARY_DISSOLUTION")
        .filter(Batch.status != "COMPLETED")
        .filter(
            ~db.session.query(AliasBatchProcessing)
            .filter(Batch.id == AliasBatchProcessing.batch_id)
            .filter(AliasBatchProcessing.status.notin_(["COMPLETED", "WITHDRAWN"]))
            .exists()
        )
        .all()
    )

    for batch in batches:
        batch.status = Batch.BatchStatus.COMPLETED
        batch.end_date = datetime.now(UTC)
        batch.save()


def stage_1_process(app: Flask):  # pylint: disable=redefined-outer-name,too-many-locals
    """Initiate dissolution process for new businesses that meet dissolution criteria."""
    try:
        # check if batch has already run today
        today_date = datetime.now(UTC).date()

        batch_today = (
            db.session.query(Batch)
            .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
            .filter(cast(Batch.start_date, Date) == today_date)
        ).all()

        if len(batch_today) > 0:
            app.logger.debug("Skipping job run since batch job has already run today.")
            return

        # get first NUM_DISSOLUTIONS_ALLOWED number of businesses
        num_dissolutions_allowed = Configuration.find_by_name(config_name="NUM_DISSOLUTIONS_ALLOWED").val
        businesses_eligible = InvoluntaryDissolutionService.get_businesses_eligible(num_dissolutions_allowed)

        # get the MAX_DISSOLUTIONS_ALLOWED number of businesses
        max_dissolutions_allowed = Configuration.find_by_name(config_name="MAX_DISSOLUTIONS_ALLOWED").val

        if len(businesses_eligible) == 0:
            app.logger.debug("Skipping job run since there are no businesses eligible for dissolution.")
            return

        # get stage_1 & stage_2 delay configs
        stage_1_delay = timedelta(days=app.config.get("STAGE_1_DELAY"))

        # create new entry in batches table
        batch = Batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                      status=Batch.BatchStatus.PROCESSING,
                      size=len(businesses_eligible),
                      max_size=max_dissolutions_allowed,
                      start_date=datetime.now(UTC))
        batch.save()
        app.logger.debug(f"New batch has been created with ID: {batch.id}")

        # create batch processing entries for each business being dissolved
        for business_elgible in businesses_eligible:
            business, ar_overdue, transition_overdue = business_elgible
            batch_processing = BatchProcessing(business_identifier=business.identifier,
                                               step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                                               status=BatchProcessing.BatchProcessingStatus.PROCESSING,
                                               created_date=datetime.now(UTC),
                                               trigger_date=datetime.now(UTC) + stage_1_delay,
                                               batch_id=batch.id,
                                               business_id=business.id)

            batch_processing.meta_data = {
                "overdueARs": ar_overdue,
                "overdueTransition": transition_overdue,
                "stage_1_date": datetime.now(UTC).isoformat()
            }
            batch_processing.save()
            app.logger.debug(f"New batch processing has been created with ID: {batch_processing.id}")


    except Exception as err:  # pylint: disable=redefined-outer-name; noqa: B902
        app.logger.error(err)


def _check_stage_1_furnishing_entries(furnishings):
    """Check furnishing entries - 2 scenarios.

    1. if email processed, and mail processed or queued(FF) (after 5 business days still not in GS).
    2. only available to send mail out, and it's processed.
    """
    email_processed = any(
        furnishing.furnishing_type == Furnishing.FurnishingType.EMAIL
        and furnishing.status == Furnishing.FurnishingStatus.PROCESSED
        for furnishing in furnishings
    )

    expected_mail_status = [Furnishing.FurnishingStatus.PROCESSED]
    # if SFTP function is off, we expect the mail status will be QUEUED or PROCESSED
    if flags.is_on("disable-dissolution-sftp-bcmail"):
        expected_mail_status.append(Furnishing.FurnishingStatus.QUEUED)

    mail_processed = any(
        (furnishing.furnishing_type == Furnishing.FurnishingType.MAIL)
        and (furnishing.status in expected_mail_status)
        for furnishing in furnishings
    )
    email_exists = any(furnishing.furnishing_type == Furnishing.FurnishingType.EMAIL for furnishing in furnishings)
    return (email_exists and email_processed and mail_processed) \
        or (not email_exists and mail_processed)


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
            BatchProcessing.trigger_date <= func.timezone("UTC", func.now())
        )
        .all()
    )

    # TODO: add check if warnings have been sent out & set batch_processing.status to error if not

    stage_2_delay = timedelta(days=app.config.get("STAGE_2_DELAY"))

    for batch_processing in batch_processings:
        furnishings = Furnishing.find_by(
            batch_id=batch_processing.batch_id,
            business_id=batch_processing.business_id
        )

        furnishing_entry_completed = _check_stage_1_furnishing_entries(furnishings)

        if not furnishing_entry_completed:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.ERROR
            batch_processing.notes = "stage 1 email or letter has not been sent"
            batch_processing.save()
            app.logger.debug(
                f"Changed Batch Processing with id: {batch_processing.id} status to Error. "
                "Stage 1 email or letter has not been sent"
            )
            continue

        eligible, _ = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
        )
        if eligible:
            batch_processing.step = BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
            batch_processing.trigger_date = datetime.now(UTC) + stage_2_delay
            app.logger.debug(f"Changed Batch Processing with id: {batch_processing.id} step to level 2.")
            if batch_processing.meta_data is None:
                batch_processing.meta_data = {}
            batch_processing.meta_data = {**batch_processing.meta_data, "stage_2_date": datetime.now(UTC).isoformat()}
        else:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN
            batch_processing.notes = "Moved back into good standing"
            app.logger.debug(f"Changed Batch Processing with id: {batch_processing.id} status to Withdrawn.")
        batch_processing.last_modified = datetime.now(UTC)
        batch_processing.save()


def stage_3_process(app: Flask):
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
            BatchProcessing.trigger_date <= func.timezone("UTC", func.now())
        )
        .all()
    )

    # TODO: add check if warnings have been sent out & set batch_processing.status to error if not

    for batch_processing in batch_processings:
        # Check if gazette furnishing entry has been completed. If not, do not transition to stage 3.
        furnishings = Furnishing.find_by(
            batch_id=batch_processing.batch_id,
            business_id=batch_processing.business_id
        )
        furnishing_entry_completed = any(
            (furnishing.furnishing_type == Furnishing.FurnishingType.GAZETTE)
            and furnishing.status == Furnishing.FurnishingStatus.PROCESSED
            for furnishing in furnishings
        )
        if not furnishing_entry_completed:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.ERROR
            batch_processing.notes = "stage 2 intent to dissolve data has not been sent"
            batch_processing.save()
            app.logger.debug(
                f"Changed Batch Processing with id: {batch_processing.id} status to Error. "
                "Stage 2 intent to dissolve data has not been sent"
            )
            continue

        eligible, _ = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
        )
        batch_processing.last_modified = datetime.now(UTC)
        if eligible:
            filing = create_invountary_dissolution_filing(batch_processing.business_id)
            app.logger.debug(f"Created Involuntary Dissolution Filing with ID: {filing.id}")
            batch_processing.filing_id = filing.id
            batch_processing.step = BatchProcessing.BatchProcessingStep.DISSOLUTION
            batch_processing.status = BatchProcessing.BatchProcessingStatus.QUEUED
            if batch_processing.meta_data is None:
                batch_processing.meta_data = {}
            batch_processing.meta_data = {**batch_processing.meta_data, "stage_3_date": datetime.now(UTC).isoformat()}
            batch_processing.save()

            put_filing_on_queue(filing.id, app)

            app.logger.debug(
                f"Batch Processing with identifier: {batch_processing.business_identifier} has been marked as queued."
            )
        else:
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN
            batch_processing.notes = "Moved back into good standing"
            batch_processing.save()

    mark_eligible_batches_completed()
    app.logger.debug("Marked batches complete when all of their associated batch_processings are completed.")


def can_run_today(cron_value: str):
    """Check if cron string is valid for today."""
    tz = pytz.timezone("US/Pacific")
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


def run(application: Flask):  # pylint: disable=redefined-outer-name
    """Run the stage 1-3 methods for dissolving businesses."""
    if application is None:
        application = create_app()

    with application.app_context():
        flag_on = flags.is_on("enable-involuntary-dissolution")
        application.logger.debug(f"enable-involuntary-dissolution flag on: {flag_on}")
        if flag_on:
            # check if batch can be run today
            stage_1_valid, stage_2_valid, stage_3_valid = check_run_schedule()
            application.logger.debug(
                f"Run schedule check: stage_1: {stage_1_valid}, stage_2: {stage_2_valid}, stage_3: {stage_3_valid}"
            )
            if not any([stage_1_valid, stage_2_valid, stage_3_valid]):
                application.logger.debug(
                    "Skipping job run since current day of the week does not match any cron schedule."
                )
                return

            if stage_1_valid:
                application.logger.debug("Entering stage 1 of involuntary dissolution job.")
                stage_1_process(application)
                application.logger.debug("Exiting stage 1 of involuntary dissolution job.")
            if stage_2_valid:
                application.logger.debug("Entering stage 2 of involuntary dissolution job.")
                stage_2_process(application)
                application.logger.debug("Exiting stage 2 of involuntary dissolution job.")
            if stage_3_valid:
                application.logger.debug("Entering stage 3 of involuntary dissolution job.")
                stage_3_process(application)
                application.logger.debug("Exiting stage 3 of involuntary dissolution job.")


if __name__ == "__main__":
    application = create_app()
    try:
        run(application)
    except Exception as err:  # pylint: disable=broad-except; Catching all errors from the frameworks
        application.logger.error(err)  # pylint: disable=no-member
        raise err
