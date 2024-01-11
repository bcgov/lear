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

"""Tests to assure the EntityRole Model.

Test-Suite to ensure that the EntityRole Model is working as expected.
"""
from datetime import datetime

from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Address, ColinEntity, LegalEntity
from legal_api.models.entity_role import EntityRole
from tests.unit.models import (
    factory_address,
    factory_completed_filing,
    factory_legal_entity,
)


def test_valid_related_entity_save(session):
    """Assert that a valid related entity role can be saved."""
    now = datetime.utcnow()

    with freeze_time(now):
        legal_entity_gp = factory_legal_entity(
            identifier="FM1234567", entity_type=LegalEntity.EntityTypes.PARTNERSHIP.value
        )
        legal_entity_1 = factory_legal_entity(identifier="BC1111111", entity_type=LegalEntity.EntityTypes.COMP)
        legal_entity_2 = factory_legal_entity(
            entity_type=LegalEntity.EntityTypes.PERSON.value, first_name="Jane", last_name="Doe"
        )

        mailing_address = factory_address(Address.MAILING)
        delivery_address = factory_address(Address.DELIVERY)
        entity_role_1 = EntityRole(
            role_type=EntityRole.RoleTypes.partner,
            legal_entity_id=legal_entity_gp.id,
            related_entity_id=legal_entity_1.id,
            appointment_date=now,
            mailing_address_id=mailing_address.id,
            delivery_address_id=delivery_address.id,
        )
        entity_role_1.save()

        entity_role_2 = EntityRole(
            role_type=EntityRole.RoleTypes.partner,
            legal_entity_id=legal_entity_gp.id,
            related_entity_id=legal_entity_2.id,
            appointment_date=now,
            mailing_address_id=mailing_address.id,
            delivery_address_id=delivery_address.id,
        )
        entity_role_2.save()

        assert entity_role_1.id
        assert entity_role_2.id

        entity_roles = legal_entity_gp.entity_roles.all()
        assert len(entity_roles) == 2

        partner_1 = next(
            entity_role for entity_role in entity_roles if entity_role.related_entity.identifier == "BC1111111"
        )
        assert partner_1.role_type == EntityRole.RoleTypes.partner
        assert partner_1.legal_entity_id is not None
        assert partner_1.mailing_address.id == mailing_address.id
        assert partner_1.delivery_address.id == delivery_address.id
        assert partner_1.related_entity.entity_type == LegalEntity.EntityTypes.COMP
        assert partner_1.appointment_date
        assert partner_1.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)
        assert partner_1.related_colin_entity_id is None
        assert partner_1.filing_id is None

        partner_2 = next(entity_role for entity_role in entity_roles if entity_role.related_entity.first_name == "Jane")
        assert partner_2.legal_entity_id is not None
        assert partner_2.role_type == EntityRole.RoleTypes.partner
        assert partner_2.mailing_address.id == mailing_address.id
        assert partner_2.delivery_address.id == delivery_address.id
        assert partner_2.related_entity.entity_type == LegalEntity.EntityTypes.PERSON
        assert partner_2.appointment_date
        assert partner_2.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)
        assert partner_2.related_colin_entity_id is None
        assert partner_2.filing_id is None


def test_valid_related_colin_entity_save(session):
    """Assert that a valid related colin entity role can be saved."""
    now = datetime.utcnow()

    with freeze_time(now):
        legal_entity_gp = factory_legal_entity(identifier="FM1234567", entity_type=LegalEntity.EntityTypes.PARTNERSHIP)
        colin_entity_1 = ColinEntity(identifier="BC1111111", organization_name="XYZ BC LTD")
        colin_entity_1.save()
        colin_entity_2 = ColinEntity(identifier="BC2222222", organization_name="ABC CCC")
        colin_entity_2.save()

        mailing_address = factory_address(Address.MAILING)
        delivery_address = factory_address(Address.DELIVERY)
        entity_role_1 = EntityRole(
            role_type=EntityRole.RoleTypes.partner,
            legal_entity_id=legal_entity_gp.id,
            related_colin_entity_id=colin_entity_1.id,
            appointment_date=now,
            mailing_address_id=mailing_address.id,
            delivery_address_id=delivery_address.id,
        )
        entity_role_1.save()

        entity_role_2 = EntityRole(
            role_type=EntityRole.RoleTypes.partner,
            legal_entity_id=legal_entity_gp.id,
            related_colin_entity_id=colin_entity_2.id,
            appointment_date=now,
            mailing_address_id=mailing_address.id,
            delivery_address_id=delivery_address.id,
        )
        entity_role_2.save()

        assert entity_role_1.id
        assert entity_role_2.id

        entity_roles = legal_entity_gp.entity_roles.all()
        assert len(entity_roles) == 2

        partner_1 = next(
            entity_role for entity_role in entity_roles if entity_role.related_colin_entity.identifier == "BC1111111"
        )
        assert partner_1.legal_entity_id is not None
        assert partner_1.role_type == EntityRole.RoleTypes.partner
        assert partner_1.mailing_address.id == mailing_address.id
        assert partner_1.delivery_address.id == delivery_address.id
        assert partner_1.related_colin_entity.organization_name == "XYZ BC LTD"
        assert partner_1.appointment_date
        assert partner_1.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)
        assert partner_1.related_entity is None
        assert partner_1.filing_id is None

        partner_2 = next(
            entity_role for entity_role in entity_roles if entity_role.related_colin_entity.identifier == "BC2222222"
        )
        assert partner_2.legal_entity_id is not None
        assert partner_2.role_type == EntityRole.RoleTypes.partner
        assert partner_2.mailing_address.id == mailing_address.id
        assert partner_2.delivery_address.id == delivery_address.id
        assert partner_2.related_colin_entity.organization_name == "ABC CCC"
        assert partner_2.appointment_date
        assert partner_2.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)
        assert partner_2.related_entity is None
        assert partner_2.filing_id is None


def test_valid_filing_entity_role_save(session):
    """Assert that a valid filing based entity role can be saved."""
    now = datetime.utcnow()

    with freeze_time(now):
        legal_entity = factory_legal_entity(
            identifier=None, entity_type=LegalEntity.EntityTypes.PERSON.value, first_name="Jane", last_name="Doe"
        )
        ar_filing = factory_completed_filing(legal_entity, ANNUAL_REPORT)

        mailing_address = factory_address(Address.MAILING)
        delivery_address = factory_address(Address.DELIVERY)
        entity_role = EntityRole(
            role_type=EntityRole.RoleTypes.completing_party,
            legal_entity_id=legal_entity.id,
            filing_id=ar_filing.id,
            appointment_date=now,
            mailing_address_id=mailing_address.id,
            delivery_address_id=delivery_address.id,
        )
        entity_role.save()
        assert entity_role.id

        entity_roles = legal_entity.entity_roles.filter(
            EntityRole.role_type == EntityRole.RoleTypes.completing_party, EntityRole.filing_id == ar_filing.id
        ).all()
        assert len(entity_roles) == 1

        entity_role = entity_roles[0]
        assert entity_role.legal_entity_id == legal_entity.id
        assert entity_role.mailing_address.id == mailing_address.id
        assert entity_role.delivery_address.id == delivery_address.id
        assert entity_role.filing_id == ar_filing.id
        assert entity_role.related_colin_entity is None
        assert entity_role.related_entity is None
        assert entity_role.appointment_date
        assert entity_role.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)

        filing_entity_roles = ar_filing.filing_entity_roles.all()
        assert len(filing_entity_roles) == 1
        filing_entity_role = filing_entity_roles[0]
        assert filing_entity_role.legal_entity_id == legal_entity.id
        assert filing_entity_role.mailing_address.id == mailing_address.id
        assert filing_entity_role.delivery_address.id == delivery_address.id
        assert filing_entity_role.filing_id == ar_filing.id
        assert filing_entity_role.related_colin_entity is None
        assert filing_entity_role.related_entity is None
        assert filing_entity_role.appointment_date
        assert filing_entity_role.appointment_date.replace(tzinfo=None) == now.replace(tzinfo=None)
