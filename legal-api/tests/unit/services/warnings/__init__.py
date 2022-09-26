from datetime import datetime
from random import randint

from datedelta import datedelta
from legal_api.models import db, Address, Business, Office, Party, PartyRole, Filing


def factory_party_person(first_name: str,
                         last_name: str) -> Party:
    party = Party(party_type='person',
                  first_name=first_name,
                  last_name=last_name)
    return party


def factory_party_organization(organization_name: str,
                               identifier: str) -> Party:
    party = Party(party_type='organization',
                  organization_name=organization_name,
                  identifier=identifier)
    return party


def factory_party_role_person(role:str, cessation_date: datetime = None):
    party_role = PartyRole(role=role, cessation_date=cessation_date)
    party_role.party = factory_party_person('jane', 'doe')
    return party_role


def factory_party_role_organization(role:str, cessation_date: datetime = None):
    party_role = PartyRole(role=role, cessation_date=cessation_date)
    party_role.party = factory_party_organization('test business name', 'FM1112222')
    return party_role


def factory_party_roles(role: str,
                        num_persons_roles: int,
                        num_org_roles: int,
                        cessation_date: datetime = None):
    party_roles = []

    # _ is used to avoid triggering sonarcloud
    for _ in range(num_persons_roles):
        person_role = factory_party_role_person(role, cessation_date)
        party_roles.append(person_role)

    # _ is used to avoid triggering sonarcloud
    for _ in range(num_org_roles):
        org_role = factory_party_role_organization(role, cessation_date)
        party_roles.append(org_role)

    return party_roles


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


def factory_business(legal_type: str, identifier: str):
    business = Business(legal_name='test business',
                        legal_type=legal_type,
                        identifier=identifier,
                        state='ACTIVE')
    return business


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


def create_business(legal_type: str,
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
                    cessation_date=None):
    business = factory_business(identifier=identifier,
                                legal_type=legal_type)
    if start_date:
        business.start_date = start_date

    if create_office:
        business_office = factory_office('businessOffice')

        if create_office_mailing_address:
            mailing_addr = factory_address('mailing')
            business_office.addresses.append(mailing_addr)

        if create_office_delivery_address:
            delivery_addr = factory_address('delivery')
            business_office.addresses.append(delivery_addr)

        business.offices.append(business_office)

    if firm_num_persons_roles > 0 or firm_num_org_roles > 0:
        firm_party_role = get_firm_party_role(legal_type)
        firm_party_roles = factory_party_roles(firm_party_role, firm_num_persons_roles, firm_num_org_roles,
                                               cessation_date)
        if create_firm_party_address:
            for party_role in firm_party_roles:
                mailing_addr = factory_address('mailing')
                mailing_addr.save()
                party_role.party.mailing_address_id = mailing_addr.id
        business.party_roles.extend(firm_party_roles)

    for idx, filing_type in enumerate(filing_types):
        filing = factory_filing(filing_type)
        has_completing_party = filing_has_completing_party[idx]
        if has_completing_party:
            completing_party_role = factory_party_role_person('completing_party')
            if create_completing_party_address:
                mailing_addr = factory_address('mailing')
                mailing_addr.save()
                completing_party_role.party.mailing_address_id = mailing_addr.id
            filing.filing_party_roles.append(completing_party_role)
        business.filings.append(filing)

    business.save()
    return business


def get_firm_party_role(legal_type: str):
    if legal_type == 'SP':
        return 'proprietor'
    elif legal_type == 'GP':
        return 'partner'
    else:
        return None


def create_filing(filing_type:str, add_completing_party=False):
    filing = factory_filing(filing_type=filing_type)
    if add_completing_party:
        party_role = factory_party_role_person('completing_party')
        filing.filing_party_roles.append(party_role)

    filing.save()
    return filing
