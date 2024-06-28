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

"""Tests to assure the Furnishing Model.

Test-Suite to ensure that the Furnishing Model is working as expected.
"""
import pytest
from legal_api.models import Furnishing
from tests.unit.models import factory_business, factory_batch

def test_valid_furnishing_save(session):
    """Assert that a valid furnishing can be saved."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    batch = factory_batch()
    furnishing = Furnishing(
        furnishing_type = Furnishing.FurnishingType.EMAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = Furnishing.FurnishingStatus.QUEUED
    )

    furnishing.save()
    assert furnishing.id


def test_find_furnishing_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    batch = factory_batch()
    furnishing = Furnishing(
        furnishing_type = Furnishing.FurnishingType.EMAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = Furnishing.FurnishingStatus.QUEUED
    )

    furnishing.save()

    res = Furnishing.find_by_id(furnishing_id=furnishing.id)

    assert res


@pytest.mark.parametrize(
    'params', [
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': None,
            'furnishing_type': None,
            'status': None,
            'grouping_identifier': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': None,
            'status': None,
            'grouping_identifier': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': None,
            'grouping_identifier': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': Furnishing.FurnishingStatus.QUEUED,
            'grouping_identifier': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': Furnishing.FurnishingStatus.QUEUED,
            'grouping_identifier': 2
        },
    ]
)
def test_find_furnishing_by(session, params):
    """Assert that the method returns correct values."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    batch = factory_batch()
    furnishing = Furnishing(
        furnishing_type = Furnishing.FurnishingType.EMAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = Furnishing.FurnishingStatus.QUEUED,
        grouping_identifier = 2
    )

    furnishing.save()

    res = Furnishing.find_by(**params)

    assert len(res) == 1
    assert res[0].id == furnishing.id


def test_get_next_grouping_identifier(session):
    """Assert that the grouping_identifier value is generated successfully."""
    first_val = Furnishing.get_next_grouping_identifier()
    assert first_val

    next_val = Furnishing.get_next_grouping_identifier()
    assert next_val
    assert next_val == first_val + 1
