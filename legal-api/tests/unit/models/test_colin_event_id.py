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

"""Tests to assure the Colin Event Id Model.

Test-Suite to ensure that the Colin Event Id Model is working as expected.
"""
from legal_api.models.colin_event_id import ColinEventId
from registry_schemas.example_data import ANNUAL_REPORT

from tests.unit.models import factory_business, factory_batch, factory_batch_processing, factory_filing


def test_valid_colin_event_id_save(session):
    """Assert that a valid Colin Event Id can be saved."""
    business_identifier = 'BC1234567'
    business = factory_business(business_identifier)
    filing = factory_filing(business, ANNUAL_REPORT)
    colin_event_id = ColinEventId(filing_id=filing.id)
    colin_event_id.save()
    assert colin_event_id.colin_event_id

    # Save with batch_processing
    batch = factory_batch()
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business_identifier
    )
    colin_event_id.batch_processing_id = batch_processing.id
    colin_event_id.batch_processing_step = batch_processing.step
    colin_event_id.save()
    assert colin_event_id.batch_processing_id
    assert colin_event_id.batch_processing_step
    assert colin_event_id.batch_processing


def test_get_by_colin_id(session):
    """Assert that the method returns correct value."""
    business_identifier = 'BC1234567'
    business = factory_business(business_identifier)
    filing = factory_filing(business, ANNUAL_REPORT)
    colin_event_id = ColinEventId(filing_id=filing.id)
    colin_event_id.save()

    res = ColinEventId.get_by_colin_id(colin_event_id.colin_event_id)

    assert res
    assert res.filing_id == colin_event_id.filing_id


def test_get_by_filing_id(session):
    """Assert that the method returns correct value."""
    business_identifier = 'BC1234567'
    business = factory_business(business_identifier)
    filing = factory_filing(business, ANNUAL_REPORT)
    colin_event_id = ColinEventId(filing_id=filing.id)
    colin_event_id.save()

    res = ColinEventId.get_by_filing_id(filing.id)

    assert res
    assert len(res) == 1
    assert res[0] == colin_event_id.colin_event_id


def test_get_by_batch_processing_id(session):
    """Assert that the method returns correct value."""
    business_identifier = 'BC1234567'
    business = factory_business(business_identifier)
    filing = factory_filing(business, ANNUAL_REPORT)
    
    batch = factory_batch()
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business_identifier
    )
    colin_event_id = ColinEventId(
        filing_id=filing.id,
        batch_processing_id = batch_processing.id,
        batch_processing_step = batch_processing.step
    )
    colin_event_id.save()

    res = ColinEventId.get_by_batch_processing_id(batch_processing.id)

    assert res
    assert len(res) == 1
    assert res[0] == colin_event_id.colin_event_id
