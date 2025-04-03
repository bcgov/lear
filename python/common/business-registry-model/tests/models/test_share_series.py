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

"""Tests to assure the ShareSeries Model.

Test-Suite to ensure that the ShareSeries Model is working as expected.
"""

from http import HTTPStatus

import pytest

from business_model.exceptions import BusinessException
from business_model.models import ShareClass, ShareSeries
from tests.models import factory_business


def test_valid_share_series_save(session):
    """Assert that a valid share series can be saved."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=500,
        special_rights_flag=False
    )
    share_series_2 = ShareSeries(
        name='Share Series 2',
        priority=2,
        max_share_flag=True,
        max_shares=1000,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)
    share_class.series.append(share_series_2)
    share_class.save()
    assert share_series_1.id
    assert share_series_2.id


def test_share_series_json(session):
    """Assert the json format of share series."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=500,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)
    share_class.save()

    share_class_json = {
        'id': share_class.id,
        'name': share_class.name,
        'priority': share_class.priority,
        'hasMaximumShares': share_class.max_share_flag,
        'maxNumberOfShares': share_class.max_shares,
        'hasParValue': share_class.par_value_flag,
        'parValue': share_class.par_value,
        'currency': share_class.currency,
        'hasRightsOrRestrictions': share_class.special_rights_flag,
        'series': [
            {
                'id': share_series_1.id,
                'name': share_series_1.name,
                'priority': share_series_1.priority,
                'hasMaximumShares': share_series_1.max_share_flag,
                'maxNumberOfShares': share_series_1.max_shares,
                'hasRightsOrRestrictions': share_series_1.special_rights_flag
            }
        ]
    }
    assert share_class_json == share_class.json


def test_invalid_share_quantity(session):
    """Assert that model validates share series share quantity."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=None,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)

    with pytest.raises(BusinessException) as share_class_error:
        share_class.save()
    session.rollback()

    assert share_class_error
    assert share_class_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_class_error.value.error == \
        f'The share series {share_series_1.name} must specify maximum number of share.'


def test_validate_share_quantity_not_exceed_class_value(session):
    """Assert that model validates share series share quantity."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=1500,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)

    with pytest.raises(BusinessException) as share_class_error:
        share_class.save()
    session.rollback()

    assert share_class_error
    assert share_class_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_class_error.value.error == \
        f'The max share quantity of {share_series_1.name} must be <= that of share class quantity.'


def test_share_quantity_when_no_max_share_for_parent(session):
    """Assert that model validates share series share quantity."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=False,
        max_shares=None,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=1500,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)
    share_class.save()
    assert share_series_1.id
