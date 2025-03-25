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
from business_model.models import Furnishing
from tests.models import factory_business, factory_batch, factory_furnishing_group

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
        status = Furnishing.FurnishingStatus.QUEUED,
        last_ar_date=business.last_ar_date,
        business_name=business.legal_name
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
            'furnishing_group_id': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': None,
            'status': None,
            'furnishing_group_id': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': None,
            'furnishing_group_id': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': Furnishing.FurnishingStatus.QUEUED,
            'furnishing_group_id': None
        },
        {
            'batch_id': None,
            'business_id': None,
            'furnishing_name': Furnishing.FurnishingType.EMAIL,
            'furnishing_type': Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
            'status': Furnishing.FurnishingStatus.QUEUED,
            'furnishing_group_id': None
        },
    ]
)
def test_find_furnishing_by(session, params):
    """Assert that the method returns correct values."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    batch = factory_batch()
    furnishing_group = factory_furnishing_group()
    furnishing = Furnishing(
        furnishing_type = Furnishing.FurnishingType.EMAIL,
        furnishing_name = Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
        batch_id = batch.id,
        business_id = business.id,
        business_identifier = business.identifier,
        status = Furnishing.FurnishingStatus.QUEUED,
        furnishing_group_id = furnishing_group.id
    )

    furnishing.save()

    res = Furnishing.find_by(**params)

    assert len(res) == 1
    assert res[0].id == furnishing.id
