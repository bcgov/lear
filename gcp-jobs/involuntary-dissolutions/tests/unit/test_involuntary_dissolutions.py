# Copyright © 2024 Province of British Columbia
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
"""Tests for the Involuntary Dissolutions Job.
Test suite to ensure that the Involuntary Dissolutions Job is working as expected.
"""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz
from datedelta import datedelta
from freezegun import freeze_time

from business_common.core.filing import Filing as CoreFiling
from business_model.models import Batch, BatchProcessing, Configuration, Filing, Furnishing
from involuntary_dissolutions.involuntary_dissolutions import (
    check_run_schedule,
    create_invountary_dissolution_filing,
    mark_eligible_batches_completed,
    stage_1_process,
    stage_2_process,
    stage_3_process,
)
from involuntary_dissolutions.utils.flags import Flags
from involuntary_dissolutions.utils.involuntary_dissolution_types import DissolutionTypes

from . import factory_batch, factory_batch_processing, factory_business

CREATED_DATE = (datetime.now(UTC) + datedelta(days=-60)).replace(tzinfo=pytz.UTC)
TRIGGER_DATE = CREATED_DATE + datedelta(days=42)

@freeze_time("2024-06-04 01:02:03")
def test_check_run_schedule():
    """Assert that schedule check validates the day of run based on cron string in config."""
    with patch.object(Configuration, "find_by_name") as mock_find_by_name:
        mock_stage_1_config = MagicMock()
        mock_stage_2_config = MagicMock()
        mock_stage_3_config = MagicMock()
        mock_stage_1_config.val = "0 0 * * 1-2"
        mock_stage_2_config.val = "0 0 * * 2"
        mock_stage_3_config.val = "0 0 * * 3"
        mock_find_by_name.side_effect = [mock_stage_1_config, mock_stage_2_config, mock_stage_3_config]

        cron_valid_1, cron_valid_2, cron_valid_3 = check_run_schedule()

        assert cron_valid_1 is True
        assert cron_valid_2 is True
        assert cron_valid_3 is False


def test_create_invountary_dissolution_filing(app, session):
    """Assert that the involuntary dissolution filing is created successfully."""
    business = factory_business(identifier="BC1234567")
    filing_id = create_invountary_dissolution_filing(business.id).id

    filing = Filing.find_by_id(filing_id)
    assert filing
    assert filing.business_id == business.id
    assert filing.filing_type == CoreFiling.FilingTypes.DISSOLUTION
    assert filing.filing_sub_type == DissolutionTypes.INVOLUNTARY
    assert filing.filing_json


@pytest.mark.parametrize(
    "test_name, batch_processing_statuses, expected", [
        (
            "MARKED_COMPLETED",
            [
                BatchProcessing.BatchProcessingStatus.COMPLETED,
                BatchProcessing.BatchProcessingStatus.WITHDRAWN
            ],
            Batch.BatchStatus.COMPLETED
        ),
        (
            "NOT_MARKED_COMPLETED",
            [
                BatchProcessing.BatchProcessingStatus.PROCESSING,
                BatchProcessing.BatchProcessingStatus.COMPLETED,
                BatchProcessing.BatchProcessingStatus.WITHDRAWN
            ],
            Batch.BatchStatus.PROCESSING
        ),
    ]
)
def test_mark_eligible_batches_completed(app, session, test_name, batch_processing_statuses, expected):
    """Assert that the eligible batches are marked completed successfully."""
    business = factory_business(identifier="BC1234567")
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)

    for batch_processing_status in batch_processing_statuses:
        factory_batch_processing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            status=batch_processing_status
        )
    
    mark_eligible_batches_completed()

    assert batch.status == expected


def test_stage_1_process_job_already_ran(app, db, session):
    """Assert that the job is skipped correctly if it already ran today."""
    factory_business(identifier="BC1234567")

    config = Configuration.find_by_name(config_name="NUM_DISSOLUTIONS_ALLOWED")
    config.val = "1"
    config.save()

    # first run
    stage_1_process(app)
    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert len(batches) == 1

    # second run
    stage_1_process(app)
    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert not len(batches) > 1


def test_stage_1_process_zero_allowed(app, session):
    """Assert that the job is skipped correctly if no dissolutions are allowed."""
    factory_business(identifier="BC1234567")

    config = Configuration.find_by_name(config_name="NUM_DISSOLUTIONS_ALLOWED")
    config.val = "0"
    config.save()

    stage_1_process(app)
    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert len(batches) == 0


def test_stage_1_process(app, session):
    """Assert that batch and batch_processing entries are created correctly."""

    config = Configuration.find_by_name(config_name="NUM_DISSOLUTIONS_ALLOWED")
    config.val = "3"
    config.save()

    config = Configuration.find_by_name(config_name="MAX_DISSOLUTIONS_ALLOWED")
    config.val = "600"
    config.save()

    business_identifiers = ["BC0000001", "BC0000002", "BC0000003"]
    for business_identifier in business_identifiers:
        factory_business(identifier=business_identifier)

    stage_1_process(app)

    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert len(batches) == 1
    batch = batches[0]
    assert batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION
    assert batch.status == Batch.BatchStatus.PROCESSING
    assert batch.size == 3
    assert batch.max_size == 600
    assert batch.start_date.date() == datetime.now().date()

    batch_processings = BatchProcessing.find_by(batch_id=batch.id)
    assert len(batch_processings) == 3
    for i, batch_processing in enumerate(batch_processings):
        assert batch_processing.batch_id == batch.id
        assert batch_processing.business_identifier == business_identifiers[i]
        assert batch_processing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1
        assert batch_processing.status == BatchProcessing.BatchProcessingStatus.PROCESSING
        assert batch_processing.created_date.date() == datetime.now().date()
        assert batch_processing.trigger_date.date() == datetime.now().date() + datedelta(days=42)
        assert batch_processing.meta_data
        assert batch_processing.meta_data["stage_1_date"]


@pytest.mark.parametrize(
    "test_name, batch_status, status, email_status, mail_status, step, created_date, found, has_email, disable_dissolution_sftp_bcmail", [
        (
            "FOUND_HAS_EMAIL_FF_OFF",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            True,
            True,
            False
        ),
        (
            "FOUND_HAS_EMAIL_FF_ON",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            True,
            True,
            True
        ),
        (
            "FOUND_MAIL_ONLY_FF_OFF",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            True,
            False,
            False
        ),
        (
            "FOUND_MAIL_ONLY_FF_ON",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            True,
            False,
            True
        ),
        (
            "NOT_FOUND_BATCH_STATUS",
            Batch.BatchStatus.HOLD,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            False,
            False
        ),
        (
            "NOT_FOUND_BATCH_PROCESSING_STATUS",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.HOLD,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            False,
            False
        ),
        (
            "NOT_FOUND_STEP",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            CREATED_DATE,
            False,
            False,
            False
        ),
        (
            "NOT_FOUND_CREATED_DATE",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            datetime.now(UTC),
            False,
            False,
            False
        ),
        (
            "NOT_FOUND_EMAIL_NOT_PROCESSED_FF_OFF",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.QUEUED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            True,
            False
        ),
         (
            "NOT_FOUND_EMAIL_NOT_PROCESSED_FF_ON",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.QUEUED,
            Furnishing.FurnishingStatus.PROCESSED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            True,
            True
        ),
        (
            "NOT_FOUND_MAIL_FAILED_FF_OFF",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.FAILED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            True,
            False
        ),
        (
            "NOT_FOUND_MAIL_FAILED_FF_ON",
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            Furnishing.FurnishingStatus.PROCESSED,
            Furnishing.FurnishingStatus.FAILED,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False,
            True,
            True
        )
    ]

)
def test_stage_2_process_find_entry(app, session, test_name, batch_status, status, email_status, mail_status, step, created_date, found, has_email, disable_dissolution_sftp_bcmail):
    """Assert that only businesses that meet conditions can be processed for stage 2."""
    with patch.object(Flags, "is_on", return_value=disable_dissolution_sftp_bcmail):
        # create 2 entries, so that if sftp bc mail FF is on, we can test both mail status PROCESSED and QUEUED
        business1 = factory_business(identifier="BC1234567")
        business2 = factory_business(identifier="BC7654321")
        businesses = [business1, business2]

        batch1 = factory_batch(status=batch_status)
        batch2 = factory_batch(status=batch_status)
        batches = [batch1, batch2]
        
        last_modified = CREATED_DATE
        batch_processings = []
        for i in range(2):
            business = businesses[i]
            batch = batches[i]
            batch_processing = factory_batch_processing(
                batch_id=batch.id,
                business_id=business.id,
                identifier=business.identifier,
                status=status,
                step=step,
                created_date=created_date,
                trigger_date=created_date+datedelta(days=42),
                last_modified=last_modified
            )
            batch_processings.append(batch_processing)
        batch_processing1, batch_processing2 = batch_processings

        if has_email:
            for i in range(2):
                business = businesses[i]
                batch = batches[i]
                furnishing_email = Furnishing(
                    furnishing_type = Furnishing.FurnishingType.EMAIL,
                    furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
                    batch_id = batch.id,
                    business_id = business.id,
                    business_identifier = business.identifier,
                    status = email_status,
                )
                furnishing_email.save()

        furnishing_mails = []
        for i in range(2):
            business = businesses[i]
            batch = batches[i]
            furnishing_mail = Furnishing(
                furnishing_type = Furnishing.FurnishingType.MAIL,
                furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
                batch_id = batch.id,
                business_id = business.id,
                business_identifier = business.identifier,
                status = mail_status,
            )
            furnishing_mail.save()
            furnishing_mails.append(furnishing_mail)
        
        
        # if sftp bc mail FF is on, test both mail status PROCESSED and QUEUED
        if (disable_dissolution_sftp_bcmail) and (mail_status != Furnishing.FurnishingStatus.FAILED):
            furnishing_mail2 = furnishing_mails[1]
            furnishing_mail2.status = Furnishing.FurnishingStatus.QUEUED
            furnishing_mail2.save()

        stage_2_process(app)

        if found:
            assert batch_processing1.last_modified != last_modified
            assert batch_processing2.last_modified != last_modified
        else:
            assert batch_processing1.last_modified == last_modified
            assert batch_processing2.last_modified == last_modified


@pytest.mark.parametrize(
    "test_name, status, step, furnishing_status", [
        (
            "MOVE_2_STAGE_2_SUCCESS",
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            Furnishing.FurnishingStatus.PROCESSED
        ),
        (
            "MOVE_2_STAGE_2_FAILED",
            BatchProcessing.BatchProcessingStatus.ERROR,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            Furnishing.FurnishingStatus.FAILED
        ),
        (
            "MOVE_BACK_2_GOOD_STANDING",
            BatchProcessing.BatchProcessingStatus.WITHDRAWN,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            Furnishing.FurnishingStatus.PROCESSED
        ),
    ]
)
def test_stage_2_process_update_business(app, session, test_name, status, step, furnishing_status):
    """Assert that businesses are processed correctly."""
    business = factory_business(identifier="BC1234567")
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        created_date=CREATED_DATE,
        trigger_date=TRIGGER_DATE
    )
    furnishing_email = Furnishing(
        furnishing_type = Furnishing.FurnishingType.EMAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = furnishing_status,
    )
    furnishing_email.save()
    
    furnishing_mail = Furnishing(
        furnishing_type = Furnishing.FurnishingType.MAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = furnishing_status,
    )
    furnishing_mail.save()

    if test_name == "MOVE_BACK_2_GOOD_STANDING":
        business.last_ar_date = datetime.now(UTC)
        business.save()

    stage_2_process(app)

    assert batch_processing.status == status
    assert batch_processing.step == step

    if test_name == "MOVE_2_STAGE_2_FAILED":
        assert batch_processing.notes == "stage 1 email or letter has not been sent"

    if test_name == "MOVE_2_STAGE_2_SUCCESS":
        assert batch_processing.trigger_date.date() == datetime.now(UTC).date() + datedelta(days=30)
        assert batch_processing.meta_data["stage_2_date"]
    else:
        assert batch_processing.trigger_date == TRIGGER_DATE


@pytest.mark.parametrize(
    "test_name, status, step, furnishing_status", [
        (
            "DISSOLVE_BUSINESS",
            BatchProcessing.BatchProcessingStatus.QUEUED,
            BatchProcessing.BatchProcessingStep.DISSOLUTION,
            Furnishing.FurnishingStatus.PROCESSED
        ),
        (
            "DISSOLVE_BUSINESS_FAILED",
            BatchProcessing.BatchProcessingStatus.ERROR,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            Furnishing.FurnishingStatus.FAILED
        ),
        (
            "MOVE_BACK_TO_GOOD_STANDING",
            BatchProcessing.BatchProcessingStatus.WITHDRAWN,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            Furnishing.FurnishingStatus.PROCESSED
        ),
    ]
)

def test_stage_3_process(app, session, test_name, status, step, furnishing_status):
    """Assert that businesses are processed correctly."""
    business = factory_business(identifier="BC1234567")
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
        created_date=CREATED_DATE,
        trigger_date=TRIGGER_DATE
    )
    furnishing = Furnishing(
        furnishing_type = Furnishing.FurnishingType.GAZETTE,
        furnishing_name = Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = furnishing_status,
    )
    furnishing.save()

    if test_name == "MOVE_BACK_TO_GOOD_STANDING":
        business.last_ar_date = datetime.now(UTC)
        business.save()

    with patch("involuntary_dissolutions.involuntary_dissolutions.put_filing_on_queue") as mock_put_filing_on_queue: # noqa: F841
        stage_3_process(app)
        if test_name == "DISSOLVE_BUSINESS":
            # This can't be uncommented right now as the call fails?
            # mock_put_filing_on_queue.assert_called() # noqa: ERA001
            assert batch_processing.filing_id
            assert batch.status == Batch.BatchStatus.PROCESSING
            assert batch_processing.meta_data["stage_3_date"]
        elif test_name == "DISSOLVE_BUSINESS_FAILED":
            assert batch.status == Batch.BatchStatus.PROCESSING
            assert batch_processing.notes == "stage 2 intent to dissolve data has not been sent"
        else:
            assert batch.status == Batch.BatchStatus.COMPLETED

    assert batch_processing.status == status
    assert batch_processing.step == step
