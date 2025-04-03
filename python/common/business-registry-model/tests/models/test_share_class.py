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

"""Tests to assure the ShareClass Model.

Test-Suite to ensure that the ShareClass Model is working as expected.
"""

from http import HTTPStatus

import pytest

from business_model.exceptions import BusinessException
from business_model.models import ShareClass
from tests.models import factory_business


def test_valid_share_class_save(session):
    """Assert that a valid share class can be saved."""
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
    share_class.save()
    assert share_class.id


def test_share_class_json(session):
    """Assert the json format of share class."""
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
        'series': []
    }
    assert share_class_json == share_class.json


def test_invalid_share_quantity(session):
    """Assert that model validates share class share quantity."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=None,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    with pytest.raises(BusinessException) as share_class_error:
        share_class.save()
    session.rollback()

    assert share_class_error
    assert share_class_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_class_error.value.error == f'The share class {share_class.name} must specify maximum number of share.'


def test_invalid_par_value(session):
    """Assert that model validates share class par value."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=None,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    with pytest.raises(BusinessException) as share_class_error:
        share_class.save()
    session.rollback()

    assert share_class_error
    assert share_class_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_class_error.value.error == f'The share class {share_class.name} must specify par value.'


def test_share_class_currency(session):
    """Assert that model validates currency."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.875,
        currency=None,
        special_rights_flag=False,
        business_id=business.id
    )
    with pytest.raises(BusinessException) as share_class_error:
        share_class.save()
    session.rollback()

    assert share_class_error
    assert share_class_error.value.status_code == HTTPStatus.BAD_REQUEST
    assert share_class_error.value.error == f'The share class {share_class.name} must specify currency.'


def test_find_by_share_class_id(session):
    """Assert that the method returns correct value."""
    identifier = 'CP1234567'
    business = factory_business(identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.875,
        currency='CAD',
        special_rights_flag=False,
        business_id=business.id
    )
    share_class.save()

    res = ShareClass.find_by_share_class_id(share_class.id)

    assert res
    assert res.json == share_class.json
