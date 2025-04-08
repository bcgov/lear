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

"""Tests for the Furnishings Job.

Test suite to ensure that the Furnishings Job stage two is working as expected.
"""
from datetime import datetime

import pytest
from datedelta import datedelta

from business_model.models import BatchProcessing, Business, Furnishing
from furnishings.services import stage_two_process

from .. import factory_batch, factory_batch_processing, factory_business, factory_furnishing


@pytest.mark.parametrize(
        'test_name, entity_type, step, new_entry', [
            (
                'BC_NEW_FURNISHING',
                Business.LegalTypes.COMP.value,
                BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
                True
            ),
            (
                'XPRO_NEW_FURNISHING',
                Business.LegalTypes.EXTRA_PRO_A.value,
                BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
                True
            ),
            (
                'STAGE_2_ALREADY_RUN',
                Business.LegalTypes.COMP.value,
                BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
                False
            ),
            (
                'NOT_IN_STAGE_2',
                Business.LegalTypes.COMP.value,
                BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                False
            )
        ]
)
def test_process_create_furnishings(app, session, test_name, entity_type, step, new_entry):
    """Assert that new furnishing entries are created correctly."""
    business = factory_business(identifier='BC1234567', entity_type=entity_type)
    batch = factory_batch()
    factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        step=step
    )

    if test_name == 'STAGE_2_ALREADY_RUN':
        existing_furnishing = factory_furnishing(
            batch_id=batch.id,
            business_id=business.id,
            identifier=business.identifier,
            furnishing_name=Furnishing.FurnishingName.INTENT_TO_DISSOLVE,
            furnishing_type=Furnishing.FurnishingType.GAZETTE,
            created_date=datetime.utcnow()+datedelta(years=1),
            last_modified=datetime.utcnow()+datedelta(years=1),
            business_name=business.legal_name
        )

    stage_two_process({})

    furnishings = Furnishing.find_by(business_id=business.id)
    if new_entry:
        assert len(furnishings) == 1
        furnishing = furnishings[0]
        assert furnishing.furnishing_type == Furnishing.FurnishingType.GAZETTE
        assert furnishing.business_name == business.legal_name
        if entity_type == Business.LegalTypes.EXTRA_PRO_A.value:
            assert furnishing.furnishing_name == Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO
        else:
            assert furnishing.furnishing_name == Furnishing.FurnishingName.INTENT_TO_DISSOLVE
    else:
        if test_name == 'STAGE_2_ALREADY_RUN':
            assert len(furnishings) == 1
            furnishing = furnishings[0]
            assert furnishing == existing_furnishing
        else:
            assert len(furnishings) == 0
