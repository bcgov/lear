from datetime import datetime
from random import randint
from typing import Final

from datedelta import datedelta
from legal_api.models import db, Address, LegalEntity, Office, Party, PartyRole, Filing, EntityRole, ColinEntity


TEST_BUSINESS_NAME: Final = 'test business name'


def factory_party_person(first_name: str,
                         last_name: str,
                         custom_id: int = None) -> Party:
    party = LegalEntity(entity_type=LegalEntity.EntityTypes.PERSON.value,
                        first_name=first_name,
                        last_name=last_name)

    if custom_id is not None:
        party.id = custom_id

    return party


def factory_party_organization(organization_name: str,
                               identifier: str,
                               custom_id: int = None) -> Party:
    party = ColinEntity(organization_name=organization_name,
                        identifier=identifier)

    if custom_id is not None:
        party.id = custom_id

    return party


def factory_party_role_person(role: EntityRole.RoleTypes,
                              cessation_date: datetime = None,
                              legal_entity = None,
                              custom_person_id: int = None):
    party_role = EntityRole(role_type=role, cessation_date=cessation_date)
    if legal_entity:
        party_role.legal_entity = legal_entity
        party_role.legal_entity_id = legal_entity.id
    if custom_person_id:
        related_entity = factory_party_person('jane', 'doe', custom_person_id)
        party_role.related_entity = related_entity
        party_role.related_entity_id = related_entity.id
    else:
        party_role.related_entity = factory_party_person('jane', 'doe')
    return party_role


def factory_party_role_organization(role: EntityRole.RoleTypes,
                                    cessation_date:
                                    datetime = None,
                                    legal_entity = None,
                                    custom_org_id: int = None):
    party_role = EntityRole(role_type=role, cessation_date=cessation_date)
    if legal_entity:
        party_role.legal_entity = legal_entity
        party_role.legal_entity_id = legal_entity.id
    if custom_org_id:
        related_colin_entity = factory_party_organization(TEST_BUSINESS_NAME, 'FM1112222', custom_org_id)
        party_role.related_colin_entity = related_colin_entity
        party_role.related_colin_entity_id = related_colin_entity.id
    else:
        party_role.related_colin_entity = factory_party_organization(TEST_BUSINESS_NAME, 'FM1112222')
    return party_role


def factory_filing_role_person(filing_id: int,
                               role:str,
                               cessation_date: datetime = None,
                               custom_person_id: int = None):
    party_role = EntityRole(filing_id=filing_id, role_type=role, cessation_date=cessation_date)
    if custom_person_id:
        legal_entity = factory_party_person('jane', 'doe', custom_person_id)
        party_role.legal_entity = legal_entity
        party_role.legal_entity_id = legal_entity.id
    else:
        party_role.legal_entity = factory_party_person('jane', 'doe')
    return party_role


def factory_filing_role_organization(filing_id: int,
                                     role:str,
                                     cessation_date: datetime = None,
                                     custom_org_id: int = None):
    party_role = EntityRole(filing_id=filing_id, role_type=role, cessation_date=cessation_date)
    if custom_org_id:
        related_colin_entity = factory_party_organization(TEST_BUSINESS_NAME, 'FM1112222', custom_org_id)
        party_role.related_colin_entity = related_colin_entity
        party_role.related_colin_entity_id = related_colin_entity.id
    else:
        party_role.related_colin_entity = factory_party_organization(TEST_BUSINESS_NAME, 'FM1112222')
    return party_role


def factory_party_roles(role: EntityRole.RoleTypes,
                        num_persons_roles: int,
                        num_org_roles: int,
                        person_cessation_dates: list = [],
                        org_cessation_dates: list = [],
                        legal_entity = None
                        ):
    entity_roles = []

    # _ is used to avoid triggering sonarcloud
    for idx in range(num_persons_roles):
        person_cessation_date = None if len(person_cessation_dates) == 0 else person_cessation_dates[idx]
        person_role = factory_party_role_person(legal_entity=legal_entity, role=role, cessation_date=person_cessation_date)
        entity_roles.append(person_role)

    # _ is used to avoid triggering sonarcloud
    for idx in range(num_org_roles):
        org_cessation_date = None if len(org_cessation_dates) == 0 else org_cessation_dates[idx]
        org_role = factory_party_role_organization(legal_entity=legal_entity, role=role, cessation_date=org_cessation_date)
        entity_roles.append(org_role)

    return entity_roles


def factory_office(office_type: str):
    office = Office(office_type=office_type)
    return office


def factory_address(address_type: str,
                    make_null_field_name=None,
                    street='some street',
                    city='victoria',
                    country='CA',
                    postal_code='v512a9',
                    region='akjsdf'):
    address = Address(address_type=address_type,
                      street=street,
                      city=city,
                      country=country,
                      postal_code=postal_code,
                      region=region)

    if make_null_field_name:
        setattr(address, make_null_field_name, None)

    return address


def factory_legal_entity(entity_type: str, identifier: str, custom_id: int = None):
    legal_entity = LegalEntity(legal_name='test business',
                        entity_type=entity_type,
                        identifier=identifier,
                        state='ACTIVE')

    if custom_id:
        legal_entity.id = custom_id

    return legal_entity


def factory_filing(filing_type: str):
    filing = Filing(_filing_type=filing_type,
                    _status=Filing.Status.COMPLETED.value,
                    filing_date=(datetime.utcnow() - datedelta(days=5)))

    filing.filing_json = {
        "filing": {
            "header": {
                "date": "2013-10-30",
                "name": filing_type,
            },
            "business": {
            },
            "registration": {
            }
        }
    }

    setattr(filing, 'skip_status_listener', True)
    return filing


def create_business(entity_type: str,
                    identifier: str,
                    create_office=False,
                    create_office_mailing_address=False,
                    create_office_delivery_address=False,
                    firm_num_persons_roles=0,
                    firm_num_org_roles=0,
                    create_firm_party_address=False,
                    filing_types=[],
                    filing_has_completing_party=[],
                    create_completing_party_address=[],
                    start_date=None,
                    person_cessation_dates=[],
                    org_cessation_dates=[]):
    legal_entity = factory_legal_entity(identifier=identifier,
                                        entity_type=entity_type)

    if start_date:
        legal_entity.start_date = start_date

    if create_office:
        business_office = factory_office('businessOffice')

        if create_office_mailing_address:
            mailing_addr = factory_address('mailing')
            business_office.addresses.append(mailing_addr)

        if create_office_delivery_address:
            delivery_addr = factory_address('delivery')
            business_office.addresses.append(delivery_addr)

        legal_entity.offices.append(business_office)

    if firm_num_persons_roles > 0 or firm_num_org_roles > 0:
        firm_entity_role = get_firm_entity_role(entity_type)
        firm_entity_roles = factory_party_roles(firm_entity_role,
                                               firm_num_persons_roles,
                                               firm_num_org_roles,
                                               person_cessation_dates,
                                               org_cessation_dates)
        if create_firm_party_address:
            for entity_role in firm_entity_roles:
                mailing_addr = factory_address('mailing')
                mailing_addr.save()
                if entity_role.related_entity:
                    entity_role.related_entity.mailing_address_id = mailing_addr.id
                else:
                    entity_role.related_colin_entity.mailing_address_id = mailing_addr.id
        legal_entity.entity_roles.extend(firm_entity_roles)

    for idx, filing_type in enumerate(filing_types):
        filing = factory_filing(filing_type)
        has_completing_party = filing_has_completing_party[idx]
        if has_completing_party:
            completing_party_role = factory_filing_role_person(filing.id, 'completing_party')
            if create_completing_party_address:
                mailing_addr = factory_address('mailing')
                mailing_addr.save()
                if completing_party_role.legal_entity:
                    completing_party_role.legal_entity.mailing_address_id = mailing_addr.id
                else:
                    completing_party_role.related_colin_entity.mailing_address_id = mailing_addr.id
            filing.filing_entity_roles.append(completing_party_role)
        legal_entity.filings.append(filing)

    legal_entity.save()
    return legal_entity


def get_firm_entity_role(entity_type: str):
    if entity_type == 'SP':
        return 'proprietor'
    elif entity_type == 'GP':
        return 'partner'
    else:
        return None


def create_filing(filing_type:str, add_completing_party=False):
    filing = factory_filing(filing_type=filing_type)
    if add_completing_party:
        party_role = factory_filing_role_person(filing.id, 'completing_party')
        filing.filing_entity_roles.append(party_role)

    filing.save()
    return filing
