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

"""Tests to assure the Batch Processing Model.

Test-Suite to ensure that the Batch Processing Model is working as expected.
"""
import json
import pytest

from legal_api.models import BatchProcessing

from tests.unit.models import factory_business, factory_batch, factory_batch_processing


def test_valid_batch_processing_save(session):
    """Assert that a valid Batch Processing can be saved."""
    business_identifier = 'FM1234567'
    business = factory_business(business_identifier)
    batch = factory_batch()
    batch_processing = BatchProcessing(
        batch_id=batch.id,
        business_id=business.id,
        business_identifier=business_identifier,
        step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        status=BatchProcessing.BatchProcessingStatus.HOLD,
        notes=''
    )
    batch_processing.save()
    assert batch_processing.id


def test_find_batch_processing_by_id(session):
    """Assert that the method returns correct value."""
    business_identifier = 'FM1234567'
    business = factory_business(business_identifier)
    batch = factory_batch()
    batch_processing = BatchProcessing(
        batch_id=batch.id,
        business_id=business.id,
        business_identifier=business_identifier,
        step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        status=BatchProcessing.BatchProcessingStatus.HOLD,
        notes=''
    )
    batch_processing.save()

    res = BatchProcessing.find_by_id(batch_processing.id)

    assert res
    assert res.step == batch_processing.step


def test_batch_processing_with_meta_data(session):
    """Assert that a batch processing with meta_data can be created and saved."""
    business_identifier = 'FM1234567'
    business = factory_business(business_identifier)
    batch = factory_batch()

    meta_data = {
        'missingARs': 1,
        'warningsSent': 2,
        'dissolutionTargetDate': '2025-02-01',
        'missingTransitionFiling': False
    }

    batch_processing = BatchProcessing()
    batch_processing.business_id = business.id
    batch_processing.batch_id = batch.id
    batch_processing.business_identifier = business_identifier
    batch_processing.step = BatchProcessing.BatchProcessingStep.DISSOLUTION
    batch_processing.status = BatchProcessing.BatchProcessingStatus.COMPLETED
    batch_processing.notes = ''
    batch_processing.meta_data = json.dumps(meta_data)
    batch_processing.save()

    assert batch_processing.id
    assert json.loads(batch_processing.meta_data) == meta_data

@pytest.mark.parametrize(
        'test_name,step,event_id,expected', [
            ("D1_NOT_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1, None, True),
            ("D1_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1, 12345, False),
            ("D2_NOT_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2, None, True),
            ("D2_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2, 12345, False),
            ("D3_NOT_SYNCED", BatchProcessing.BatchProcessingStep.DISSOLUTION, None, False),
            ("D3_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.DISSOLUTION, 12345, False),
        ]
)
def test_get_completed_filings_for_colin(session, test_name, step, event_id, expected):
    """Assert that eligible batch processing for colin sync are returned."""
    from legal_api.models import Batch
    from legal_api.models.colin_event_id import ColinEventId

    # Setup
    business_identifier = 'BC1234567'
    business = factory_business(business_identifier)
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        step=step
    )
    if event_id:
        colin_event_id = ColinEventId()
        colin_event_id.colin_event_id = event_id
        colin_event_id.batch_processing_id = batch_processing.id
        colin_event_id.batch_processing_step = batch_processing.step
        colin_event_id.save()

    # Test
    batch_processings = BatchProcessing.get_eligible_batch_processings_for_colin()
    batch_processings = batch_processings.get("batch_processings")
    if expected:
        print(batch_processings[0].colin_event_ids)
        assert len(batch_processings) == 1
    else:
        assert len(batch_processings) == 0
