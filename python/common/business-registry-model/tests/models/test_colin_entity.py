# Copyright © 2023 Province of British Columbia
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

"""Tests to assure the ColinEntity Model.

Test-Suite to ensure that the ColinEntity Model is working as expected.
"""

from business_model import Address, ColinEntity
from tests.models import factory_address


def test_valid_colin_entity_save(session):
    """Assert that a valid role address can be saved."""
    mailing_address = factory_address(Address.MAILING)
    delivery_address = factory_address(Address.DELIVERY)

    colin_entity = ColinEntity(
        organization_name="XYZ BC LTD",
        identifier="BC1234567",
        email="no_one@never.get",
        mailing_address_id=mailing_address.id,
        delivery_address_id=delivery_address.id,
    )
    colin_entity.save()

    # verify
    assert colin_entity.id
