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
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz
from datedelta import datedelta
from legal_api.core.filing import Filing as CoreFiling
from legal_api.models import Batch, BatchProcessing, Configuration, Filing
from legal_api.services.filings.validations.dissolution import DissolutionTypes

from involuntary_dissolutions import (
    check_run_schedule,
    create_invountary_dissolution_filing,
    mark_eligible_batches_completed,
    put_filing_on_queue,
    stage_1_process,
    stage_2_process,
    stage_3_process,
)

from . import factory_batch, factory_batch_processing, factory_business


CREATED_DATE = (datetime.utcnow() + datedelta(days=-60)).replace(tzinfo=pytz.UTC)
TRIGGER_DATE = CREATED_DATE + datedelta(days=42)


def test_check_run_schedule():
    """Assert that schedule check validates the day of run based on cron string in config."""
    with patch.object(Configuration, 'find_by_name') as mock_find_by_name:
        mock_stage_1_config = MagicMock()
        mock_stage_2_config = MagicMock()
        mock_stage_3_config = MagicMock()
        mock_stage_1_config.val = '0 0 * * 1-2'
        mock_stage_2_config.val = '0 0 * * 2'
        mock_stage_3_config.val = '0 0 * * 3'
        mock_find_by_name.side_effect = [mock_stage_1_config, mock_stage_2_config, mock_stage_3_config]

        with patch('involuntary_dissolutions.datetime', wraps=datetime) as mock_datetime:
            mock_datetime.today.return_value = datetime(2024, 6, 4, 1, 2, 3, 4)
            cron_valid_1, cron_valid_2, cron_valid_3 = check_run_schedule()

            assert cron_valid_1 is True
            assert cron_valid_2 is True
            assert cron_valid_3 is False


def test_create_invountary_dissolution_filing(app, session):
    """Assert that the involuntary dissolution filing is created successfully."""
    business = factory_business(identifier='BC1234567')
    filing_id = create_invountary_dissolution_filing(business.id).id

    filing = Filing.find_by_id(filing_id)
    assert filing
    assert filing.business_id == business.id
    assert filing.filing_type == CoreFiling.FilingTypes.DISSOLUTION
    assert filing.filing_sub_type == DissolutionTypes.INVOLUNTARY
    assert filing.filing_json


@pytest.mark.parametrize(
    'test_name, batch_processing_statuses, expected', [
        (
            'MARKED_COMPLETED',
            [
                BatchProcessing.BatchProcessingStatus.COMPLETED,
                BatchProcessing.BatchProcessingStatus.WITHDRAWN
            ],
            Batch.BatchStatus.COMPLETED
        ),
        (
            'NOT_MARKED_COMPLETED',
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
    business = factory_business(identifier='BC1234567')
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


def test_stage_1_process_job_already_ran(app, session):
    """Assert that the job is skipped correctly if it already ran today."""
    factory_business(identifier='BC1234567')

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
    factory_business(identifier='BC1234567')

    config = Configuration.find_by_name(config_name='NUM_DISSOLUTIONS_ALLOWED')
    config.val = '0'
    config.save()

    stage_1_process(app)
    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert len(batches) == 0


def test_stage_1_process(app, session):
    """Assert that batch and batch_processing entries are created correctly."""
    business_identifiers = ['BC0000001', 'BC0000002', 'BC0000003']
    for business_identifier in business_identifiers:
        factory_business(identifier=business_identifier)

    stage_1_process(app)

    batches = Batch.find_by(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION)
    assert len(batches) == 1
    batch = batches[0]
    assert batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION
    assert batch.status == Batch.BatchStatus.PROCESSING
    assert batch.size == 3
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


@pytest.mark.parametrize(
    'test_name, batch_status, status, step, created_date, found', [
        (
            'FOUND',
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            True
        ),
        (
            'NOT_FOUND_BATCH_STATUS',
            Batch.BatchStatus.HOLD,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False
        ),
        (
            'NOT_FOUND_BATCH_PROCESSING_STATUS',
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.HOLD,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            CREATED_DATE,
            False
        ),
        (
            'NOT_FOUND_STEP',
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
            CREATED_DATE,
            False
        ),
        (
            'NOT_FOUND_CREATED_DATE',
            Batch.BatchStatus.PROCESSING,
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
            datetime.utcnow(),
            False
        )
    ]

)
def test_stage_2_process_find_entry(app, session, test_name, batch_status, status, step, created_date, found):
    """Assert that only businesses that meet conditions can be processed for stage 2."""
    business = factory_business(identifier='BC1234567')

    batch = factory_batch(status=batch_status)
    last_modified = CREATED_DATE
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

    stage_2_process(app)

    if found:
        assert batch_processing.last_modified != last_modified
    else:
        assert batch_processing.last_modified == last_modified


@pytest.mark.parametrize(
    'test_name, status, step', [
        (
            'MOVE_2_STAGE_2',
            BatchProcessing.BatchProcessingStatus.PROCESSING,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
        (
            'MOVE_BACK_2_GOOD_STANDING',
            BatchProcessing.BatchProcessingStatus.WITHDRAWN,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1
        ),
    ]
)
def test_stage_2_process_update_business(app, session, test_name, status, step):
    """Assert that businesses are processed correctly."""
    business = factory_business(identifier='BC1234567')
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        created_date=CREATED_DATE,
        trigger_date=TRIGGER_DATE
    )

    if test_name == 'MOVE_BACK_2_GOOD_STANDING':
        business.last_ar_date = datetime.utcnow()
        business.save()

    stage_2_process(app)

    assert batch_processing.status == status
    assert batch_processing.step == step

    if test_name == 'MOVE_2_STAGE_2':
        assert batch_processing.trigger_date.date() == datetime.utcnow().date() + datedelta(days=30)
    else:
        assert batch_processing.trigger_date == TRIGGER_DATE

@pytest.mark.parametrize(
    'test_name, status, step', [
        (
            'DISSOLVE_BUSINESS',
            BatchProcessing.BatchProcessingStatus.QUEUED,
            BatchProcessing.BatchProcessingStep.DISSOLUTION
        ),
        (
            'MOVE_BACK_TO_GOOD_STANDING',
            BatchProcessing.BatchProcessingStatus.WITHDRAWN,
            BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2
        ),
    ]
)
@pytest.mark.asyncio
async def test_stage_3_process(app, session, test_name, status, step):
    """Assert that businesses are processed correctly."""
    business = factory_business(identifier='BC1234567')
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
        created_date=CREATED_DATE,
        trigger_date=TRIGGER_DATE
    )

    if test_name == 'MOVE_BACK_TO_GOOD_STANDING':
        business.last_ar_date = datetime.utcnow()
        business.save()

    with patch('involuntary_dissolutions.put_filing_on_queue') as mock_put_filing_on_queue:
        qsm = MagicMock()
        await stage_3_process(app, qsm)
        if test_name == 'DISSOLVE_BUSINESS':
            mock_put_filing_on_queue.assert_called()
            assert batch_processing.filing_id

    assert batch_processing.status == status
    assert batch_processing.step == step

    assert batch.status == Batch.BatchStatus.COMPLETED
