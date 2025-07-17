# Copyright © 2025 Province of British Columbia
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

"""Tests to assure the DCBusinessUser Model.

Test-Suite to ensure that the DCBusinessUser Model is working as expected.
"""


from business_model.models import DCBusinessUser
from tests.models import factory_business, factory_user


def test_valid_dc_business_user_save(session):
    """Assert that a valid dc_business_user can be saved."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    user = factory_user('test', 'Test', 'User')
    business_user = create_dc_business_user(business, user)
    assert business_user.id


def test_find_by_id(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    user = factory_user('test', 'Test', 'User')
    business_user = create_dc_business_user(business, user)

    res = DCBusinessUser.find_by_id(business_user.id)

    assert res
    assert res.id == business_user.id


def test_find_by(session):
    """Assert that the method returns correct value."""
    identifier = 'FM1234567'
    business = factory_business(identifier)
    user = factory_user('test', 'Test', 'User')
    business_user = create_dc_business_user(business, user)

    res = DCBusinessUser.find_by(business_id=business.id, user_id=user.id)

    assert res
    assert res.id == business_user.id


def create_dc_business_user(business, user) -> DCBusinessUser:
    """Create new dc_business_user object."""
    business_user = DCBusinessUser(
        business_id=business.id,
        user_id=user.id
    )
    business_user.save()
    return business_user