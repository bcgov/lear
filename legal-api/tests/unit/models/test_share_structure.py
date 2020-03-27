# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the ShareStructure Model.

Test-Suite to ensure that the ShareStructure Model is working as expected.
"""

from http import HTTPStatus

import pytest

from legal_api.exceptions import BusinessException
from legal_api.models import ShareStructure
from tests.unit.models import factory_business


def test_valid_share_class_save(session):
    """Assert that a valid share class can be saved."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareStructure(
        name='Share Class 1',
        share_type='class',
        priority=1,
        max_shares=1000,
        par_value=0.852,
        currency='CAD',
        special_rights=False
    )
    share_class.business_id = business.id
    share_class.save()
    assert share_class.id


def test_share_class_series_save_to_business(session):
    """Assert that a share class with share series can be saved to business."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareStructure(
        name='Share Class 1',
        share_type='class',
        priority=1,
        max_shares=1000,
        par_value=0.852,
        currency='CAD',
        special_rights=False
    )
    share_series_1 = ShareStructure(
        name='Share Series 1',
        share_type='series',
        priority=1,
        max_shares=200,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=None
    )
    share_series_2 = ShareStructure(
        name='Share Series 2',
        share_type='series',
        priority=2,
        max_shares=300,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=None
    )

    share_class.series.append(share_series_1)
    share_class.series.append(share_series_2)
    business.shares.append(share_class)
    business.save()

    assert share_class.id
    assert share_series_1.id
    assert share_series_2.id
    assert share_series_1.parent_share_id == share_class.id
    assert share_series_2.parent_share_id == share_class.id
    assert len(business.shares.all()) == 1


def test_share_class_json(session):
    """Assert the json format of share structure."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareStructure(
        name='Share Class 1',
        share_type='class',
        priority=1,
        max_shares=1000,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=business.id
    )
    share_series_1 = ShareStructure(
        name='Share Series 1',
        share_type='series',
        priority=1,
        max_shares=200,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=None
    )
    share_series_2 = ShareStructure(
        name='Share Series 2',
        share_type='series',
        priority=2,
        max_shares=300,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=None
    )

    share_class.series.append(share_series_1)
    share_class.series.append(share_series_2)
    share_class.save()

    res = share_class.json
    res.pop('id')
    res['series'][0].pop('id')
    res['series'][1].pop('id')

    share_class_json = {
        'name': 'Share Class 1',
        'shareStructureType': 'class',
        'priority': 1,
        'maxNumberOfShares': 1000,
        'parValue': 0.852,
        'currency': 'CAD',
        'hasRightsOrRestrictions': False,
        'series': [
            {
                'name': 'Share Series 1',
                'shareStructureType': 'series',
                'priority': 1,
                'maxNumberOfShares': 200,
                'parValue': 0.852,
                'currency': 'CAD',
                'hasRightsOrRestrictions': False,
                'series': []
            },
            {
                'name': 'Share Series 2',
                'shareStructureType': 'series',
                'priority': 2,
                'maxNumberOfShares': 300,
                'parValue': 0.852,
                'currency': 'CAD',
                'hasRightsOrRestrictions': False,
                'series': []
            }
        ]
    }
    assert share_class_json == res


def test_invalid_share(session):
    """Assert the share structure model validates the type correctly."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareStructure(
        name='Share Class 1',
        share_type='series',
        priority=1,
        max_shares=1000,
        par_value=0.852,
        currency='CAD',
        special_rights=False,
        business_id=business.id
    )

    with pytest.raises(BusinessException) as share_type_error:
        share_class.save()
    session.rollback()

    assert share_type_error
    assert share_type_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_type_error.value.error == 'The share structure Share Class 1 has invalid type.'
