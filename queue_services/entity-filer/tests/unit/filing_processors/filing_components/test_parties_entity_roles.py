# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the business filing component processors.

Note: This first tests the building_blocks
It then uses those blocks in subsequent tests for more complex scenarios


The party component must handle:
- managing a unique entity
- the entity can have a unique Address per role set (all the roles in 1 Filing)
- the following role types.
Key:
C - Create if it doesn't exist
U - If it exists, update it
D - If one exists and a new one is C, then delete the old one
  - or if the cessation_date is set
  - Deletes are a SAVE & THEN DELETE to force a copy into the _history table
--
                                                         LINKED TO
  ROLE               PERSON    ORG (incl COLIN)      FILING     LEGAL ENTITY
  ----------------   ------    -----                 -------    ------------
 Applicant             X                                C
 Completing Party      X        X                       C
 Custodian             X        X                                   CUD
 Director              X                                            CUD
 Incorporator          X        X                      CU           CU
 Liquidator            X                                            CUD
 Partner               X        X                                   CUD 
 Proprietor            X        X                                    C

"""
import json
import datetime
from contextlib import suppress
from copy import deepcopy
from random import randint

import pytest
from business_model import Address
from business_model import EntityRole
from business_model import Filing
from business_model import LegalEntity
from sql_versioning import history_cls
from sql_versioning import versioned_session

from tests.unit import nested_session

from entity_filer.exceptions import BusinessException
from entity_filer.exceptions import ErrorCode
from entity_filer.exceptions import get_error_message
from entity_filer.filing_processors.filing_components.parties import (
    merge_entity_role_to_filing,
    create_entity_with_addresses,
    get_address_for_filing,
    map_schema_role_to_enum,
    merge_all_parties,
)


BASE_TEMPLATE ={
    "roles": [],
    "mailingAddress": {
        "postalCode": "N2E 3J7",
        "addressCity": "Kitchener",
        "addressRegion": "ON",
        "streetAddress": "45-225 Country Hill Dr",
        "addressCountry": "CA",
        "streetAddressAdditional": "",
    },
    "deliveryAddress": {
        "postalCode": "N2E 3J7",
        "addressCity": "Kitchener",
        "addressRegion": "ON",
        "streetAddress": "45-225 Country Hill Dr",
        "addressCountry": "CA",
        "streetAddressAdditional": "",
    },
}

PERSON_TEMPLATE = {
    "officer": {
        "id": 1,
        "email": "test@example.com",
        "organizationName": "",
        "lastName": "Test abc",
        "firstName": "Test abc",
        "partyType": "person",
        "middleName": "",
    }, **BASE_TEMPLATE
}

ORG_TEMPLATE = {
    "officer": {
        "email": "test@test.com",
        "identifier": "BC1234567",
        "organizationName": "BC Example Ltd.",
        "lastName": None,
        "firstName": None,
        "partyType": "organization",
        "middleName": None,
    }, **BASE_TEMPLATE
}

PARTY_TEMPLATE = {
    "officer": {
        "id": 1,
        "email": "test@test.com",
        "identifier": "BC1234567",
        "organizationName": "BC Example Ltd.",
        "lastName": None,
        "firstName": None,
        "partyType": "organization",
        "middleName": None,
    },
}
#        test_name,   schema_role, is_person, is_org, person_actions, org_actions
TEST_SCHEMA_ROLES =[
        ('Applicant', 'Applicant', True, False, ['C',], []),
        # ('Completing Party', 'Completing Party', True, True, ['C',], []),
        # ('Custodian', 'Custodian', True, True, ['C',], []),
        # ('Director', 'Director', True, False, ['C',], []),
        # ('Incorporator', 'Incorporator', True, True, ['C',], []),
        # ('Liquidator', 'Liquidator', True, False, ['C',], []),
        # ('Partner', 'Partner', True, True, ['C',], []),
        # ('Proprietor', 'Proprietor', True, True, ['C',], []),
]
def common_setup():
        base_legal_entity = LegalEntity()
        base_legal_entity.save()
        # setup Filing
        filing = Filing()
        filing.legal_entity_id = base_legal_entity.id
        filing.save() 
        base_legal_entity.change_filing_id = filing.id
        base_legal_entity.save()

        return base_legal_entity, filing

def helper_create_person(person_dict: dict) -> LegalEntity:
    # identifier= person_dict['officer'].get('identifier')
    entity = LegalEntity(
        first_name=person_dict.get('officer',{}).get('firstName'),
        last_name=person_dict.get('officer',{}).get('lastName'),
        middle_initial=person_dict.get('officer',{}).get('middleName'),
        entity_type=LegalEntity.EntityTypes.PERSON,
    )
    mail = Address(address_type=Address.MAILING)
    mail.save()
    delivery = Address(address_type=Address.DELIVERY)
    delivery.save()
    entity.mailing_address_id = mail.id
    entity.delivery_address_id = delivery.id
    entity.save()
    return entity
     

#        test_name,   schema_role, is_person, is_org, person_actions, org_actions
TEST_PARTY_ROLES =[
        ('Applicant-Person', 'Applicant', PERSON_TEMPLATE),
        ('Completing Party', 'Completing Party', PERSON_TEMPLATE),
        ('Custodian', 'Custodian', PERSON_TEMPLATE),
        ('Director', 'Director', PERSON_TEMPLATE),
        ('Incorporator', 'Incorporator', PERSON_TEMPLATE),
        ('Liquidator', 'Liquidator', PERSON_TEMPLATE),
        ('Partner', 'Partner', PERSON_TEMPLATE),
        ('Proprietor', 'Proprietor', PERSON_TEMPLATE), # This role does nothing
]


@pytest.mark.parametrize(
        "test_name,schema_role,template",
        TEST_PARTY_ROLES
)
def test_person_and_role_doesnt_exist(session, test_name, schema_role, template):
    """Test where no role or person exists.
    
    Assumption: Entity exists.
    """
    print(f' test_name: {test_name}')
    with nested_session(session):
        base_legal_entity, filing = common_setup()

        le_test = deepcopy(template)
        with suppress(KeyError):
            le_test["officer"].pop("id")  # not an existing person
            le_test["officer"].pop("identifier")  # not an existing person
        le_test["roles"] = [
            {"roleType": schema_role, "appointmentDate": "2020-08-05"},
        ]
        wrapper = {
            "parties": [
                le_test,
            ]
        }
        errors = merge_all_parties(base_legal_entity, filing, wrapper)

    assert not errors
    
    if schema_role not in ['Proprietor',]:
        entity_roles = EntityRole.get_entity_roles_by_filing(filing_id=filing.id)
        assert len(entity_roles) == len(le_test["roles"])
        assert entity_roles[0].role_type == map_schema_role_to_enum(schema_role)


@pytest.mark.parametrize(
        "test_name,schema_role,template",
        TEST_PARTY_ROLES
)
def test_person_exists_but_role_doesnt_exist(session, test_name, schema_role, template):
    """Test where the person exists but no role exists.
    
    Assumption: Entity exists.
    """
    print(f' test_name: {test_name}')
    with nested_session(session):
        base_legal_entity, filing = common_setup()

        person = helper_create_person(PERSON_TEMPLATE)

        le_test = deepcopy(PERSON_TEMPLATE)
        le_test["officer"]["id"] = person.id
        le_test["officer"]["lastName"] = "le_test"
        le_test["roles"] = [
            {"roleType": schema_role, "appointmentDate": "2020-08-05"},
        ]
        wrapper = {
            "parties": [
                le_test,
            ]
        }
        errors = merge_all_parties(base_legal_entity, filing, wrapper)
        # session.commit()

        assert not errors
        
        if schema_role not in ['Proprietor',]:
            entity_roles = EntityRole.get_entity_roles_by_filing(filing_id=filing.id)
            assert len(entity_roles) == 1
            assert len(entity_roles) == len(le_test["roles"])
            assert entity_roles[0].role_type == map_schema_role_to_enum(schema_role)
            assert entity_roles[0].related_entity == person

@pytest.mark.parametrize(
        "test_name,schema_role,template",
        TEST_PARTY_ROLES
)
def test_person_and_role_exists(session, test_name, schema_role, template):
    """Test where the person and role exists.
    
    Assumption: Entity exists.
    """
    print(f' test_name: {test_name}')
    if schema_role in ['Completing Party',]:
        # Skip test if EntityRole couldn't exist for role
        pytest.skip()
    
    with nested_session(session):
        base_legal_entity, filing = common_setup()
        person = helper_create_person(PERSON_TEMPLATE)
        entity_role = EntityRole(
            appointment_date=filing.effective_date,
            delivery_address_id=person.entity_delivery_address.id,
            filing_id=filing.id,
            legal_entity_id=base_legal_entity.id,
            mailing_address_id=person.entity_mailing_address.id,
            related_entity_id=person.id,
            role_type=map_schema_role_to_enum(schema_role)
        )
        entity_role.save()

        le_test = deepcopy(PERSON_TEMPLATE)
        le_test["officer"]["id"] = person.id
        le_test["officer"]["lastName"] = "le_test"
        le_test["roles"] = [
            {"roleType": schema_role, "appointmentDate": "2020-08-05"},
        ]
        wrapper = {
            "parties": [
                le_test,
            ]
        }
        errors = merge_all_parties(base_legal_entity, filing, wrapper)

    assert not errors
    
    if schema_role not in ['Proprietor',]:
        entity_roles = EntityRole.get_entity_roles_by_filing(filing_id=filing.id)
        assert len(entity_roles) == 1
        assert len(entity_roles) == len(le_test["roles"])
        assert entity_roles[0].role_type == map_schema_role_to_enum(schema_role)
        assert entity_roles[0].related_entity_id == person.id

@pytest.mark.parametrize(
        "test_name,schema_role,template",
        TEST_PARTY_ROLES
)
def test_person_and_role_exists_cessation_date_set(session, test_name, schema_role, template):
    """Test where the person and role exists and the role is ceased.
    
    Assumption: Entity exists.
    """
    print(f' test_name: {test_name}')
    if schema_role in ['Completing Party',]:
        # Skip test if EntityRole couldn't exist for role
        pytest.skip()

    versioned_session(session)
    with nested_session(session):
        base_legal_entity, filing = common_setup()
        person = helper_create_person(PERSON_TEMPLATE)
        entity_role = EntityRole(
            appointment_date=filing.effective_date,
            delivery_address_id=person.entity_delivery_address.id,
            filing_id=filing.id,
            legal_entity_id=base_legal_entity.id,
            mailing_address_id=person.entity_mailing_address.id,
            related_entity_id=person.id,
            role_type=map_schema_role_to_enum(schema_role)
        )
        entity_role.save()

        cessation_date = datetime.datetime.now()

        le_test = deepcopy(PERSON_TEMPLATE)
        le_test["officer"]["id"] = person.id
        le_test["officer"]["lastName"] = "le_test"
        le_test["roles"] = [
            {"roleType": schema_role,
             "appointmentDate": "2020-08-05",
             "cessationDate": cessation_date.isoformat()
            },
        ]
        wrapper = {
            "parties": [
                le_test,
            ]
        }
        errors = merge_all_parties(base_legal_entity, filing, wrapper)

        # session.commit()

        assert not errors
    
        if schema_role not in ['Proprietor',]:
            entity_roles = EntityRole.get_entity_roles_by_filing(filing_id=filing.id)
            assert len(entity_roles) == 0

            historical_roles = EntityRole.get_entity_roles_history_by_filing(filing_id=filing.id)
            number_of_historical_roles = len(historical_roles)
            assert  number_of_historical_roles >= 2
            assert historical_roles[number_of_historical_roles-1].role_type == map_schema_role_to_enum(schema_role)
            assert historical_roles[number_of_historical_roles-1].related_entity_id == person.id
            assert historical_roles[number_of_historical_roles-1].cessation_date.replace(tzinfo=None) == cessation_date


def test_directors_exist_but_not_in_filing(session):
    """Test where the directors (can only be natural persons) but aren't in the filing.
    
    This will mean existing directors are deleted, and available in the history,
    along with a cessation date of the filing.
    """
    schema_role = 'Director'
    versioned_session(session)
    with nested_session(session):
        base_legal_entity, filing = common_setup()
        for i in range(2):
            person_proto = deepcopy(PERSON_TEMPLATE)
            person_proto['officer']['lastName'] = f'director {i}'
            person = helper_create_person(person_proto)
            entity_role = EntityRole(
                appointment_date=filing.effective_date,
                delivery_address_id=person.entity_delivery_address.id,
                filing_id=filing.id,
                legal_entity_id=base_legal_entity.id,
                mailing_address_id=person.entity_mailing_address.id,
                related_entity_id=person.id,
                role_type=map_schema_role_to_enum(schema_role)
            )
            entity_role.save()
        
        le_test = deepcopy(PERSON_TEMPLATE)
        le_test["officer"].pop("id")
        le_test["officer"]["lastName"] = "le_test"
        le_test["roles"] = [
            {"roleType": schema_role,
             "appointmentDate": "2020-08-05",
            },
        ]
        wrapper = {
            "parties": [
                le_test,
            ]
        }
        errors = merge_all_parties(base_legal_entity, filing, wrapper)

        assert not errors

        current_entity_roles = EntityRole.get_parties_by_role(base_legal_entity.id, map_schema_role_to_enum(schema_role))

        assert len(current_entity_roles) == 1
        
        historical_roles = EntityRole.get_entity_roles_history_by_filing(filing_id=filing.id)
        number_of_historical_roles = len(historical_roles)
        # Should be at least 2 records for each historical role.
        assert  number_of_historical_roles == 4


# def test_add_entity_role_to_filing(session):
#     """Assert that 'add_entity_role_to_filing' is working correctly."""
#     # Setup
#     party_le = LegalEntity()
#     party_le.save()

#     filing = Filing(effective_date=datetime.datetime.now())
#     filing.save()

#     delivery_address = Address()
#     delivery_address.save()

#     mailing_address = Address()
#     mailing_address.save()

#     role = EntityRole.RoleTypes.director

#     # Test
#     entity_role = add_entity_role_to_filing(
#         party_le=party_le,
#         filing=filing,
#         role=role,
#         delivery_address=delivery_address,
#         mailing_address=mailing_address,
#         base_entity=None,
#     )
#     # Confirm
#     assert entity_role
#     assert entity_role.id
#     assert entity_role.appointment_date == filing.effective_date
#     assert entity_role.cessation_date is None
#     assert entity_role.delivery_address_id == delivery_address.id
#     assert entity_role.mailing_address_id == mailing_address.id
#     assert entity_role.role_type == role


# def test_create_person_entity_with_addresses(session):
#     """Test that a simple setup is created, and that a non-person type throws."""
#     # test success
#     legal_entity: LegalEntity = create_entity_with_addresses(PARTY_TEMPLATE)

#     assert legal_entity
#     assert legal_entity.entity_type == LegalEntity.EntityTypes.PERSON
#     assert legal_entity.mailing_address_id
#     assert legal_entity.delivery_address_id

#     # test failure of LE type is not a person
#     party = deepcopy(PARTY_TEMPLATE)
#     party["officer"]["partyType"] = LegalEntity.EntityTypes.BCOMP
#     with pytest.raises(Exception):
#         legal_entity: LegalEntity = create_entity_with_addresses(party)


# def test_get_address_for_filing(session):
#     """Test that addresses get resolved correctly."""
#     # party_address: Address,
#     address_dict: dict = {
#         "postalCode": "V8W 3H2",
#         "addressCity": "Victoria",
#         "addressRegion": "BC",
#         "streetAddress": "735 Broughton Street",
#         "addressCountry": "CA",
#         "streetAddressAdditional": "",
#     }
#     address = Address(
#         street=address_dict["streetAddress"],
#         city=address_dict["addressCity"],
#         country=address_dict["addressCountry"],
#         postal_code=address_dict["postalCode"],
#         region=address_dict["addressRegion"],
#         delivery_instructions=address_dict.get("deliveryInstructions", "").upper(),
#     )

#     resolved_address = get_address_for_filing(address, address_dict)

#     assert resolved_address == address
