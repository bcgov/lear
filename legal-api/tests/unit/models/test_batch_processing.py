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

from legal_api.models import BatchProcessing

from tests.unit.models import factory_business, factory_batch


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

