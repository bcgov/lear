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

"""Tests to assure the RoleAddress Model.

Test-Suite to ensure that the RoleAddress Model is working as expected.
"""

from legal_api.models import Address, RoleAddress
from legal_api.models.entity_role import EntityRole
from tests.unit.models import factory_address, factory_legal_entity


def test_valid_role_address_save(session):
    """Assert that a valid role address can be saved."""
    identifier = "BC1234567"
    legal_entity = factory_legal_entity(identifier)
    mailing_address = factory_address(Address.MAILING)
    delivery_address = factory_address(Address.DELIVERY)

    role_address_1 = RoleAddress(
        role_type=EntityRole.RoleTypes.partner,
        legal_entity_id=legal_entity.id,
        mailing_address_id=mailing_address.id,
        delivery_address_id=delivery_address.id,
    )
    role_address_1.save()

    role_address_2 = RoleAddress(
        role_type=EntityRole.RoleTypes.director,
        legal_entity_id=legal_entity.id,
        mailing_address_id=mailing_address.id,
        delivery_address_id=delivery_address.id,
    )
    role_address_2.save()

    # verify
    assert role_address_1.id
    assert role_address_2.id
    legal_entity.role_addresses.all()
    role_addresses = legal_entity.role_addresses.all()
    assert len(role_addresses) == 2
    assert any(role_address.role_type == EntityRole.RoleTypes.partner for role_address in role_addresses)
    assert any(role_address.role_type == EntityRole.RoleTypes.director for role_address in role_addresses)
