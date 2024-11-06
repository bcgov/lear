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
"""This module contains all of the Legal Filing specific component processors."""
from __future__ import annotations

from typing import Dict

import pycountry
from legal_api.models import Address, Office, Party, PartyRole

from entity_filer.filing_processors.filing_components import (
    aliases,
    business_info,
    business_profile,
    filings,
    name_request,
    resolutions,
    shares,
)


JSON_ROLE_CONVERTER = {
    'custodian': PartyRole.RoleTypes.CUSTODIAN.value,
    'completing party': PartyRole.RoleTypes.COMPLETING_PARTY.value,
    'director': PartyRole.RoleTypes.DIRECTOR.value,
    'incorporator': PartyRole.RoleTypes.INCORPORATOR.value,
    'proprietor': PartyRole.RoleTypes.PROPRIETOR.value,
    'partner': PartyRole.RoleTypes.PARTNER.value,
    'applicant': PartyRole.RoleTypes.APPLICANT.value,
}


def create_address(address_info: Dict, address_type: str) -> Address:
    """Create an address."""
    if not address_info:
        return Address()

    db_address_type = address_type.replace('Address', '')

    address = Address(
        street=address_info.get('streetAddress') or '',
        street_additional=address_info.get('streetAddressAdditional') or '',
        city=address_info.get('addressCity') or '',
        region=address_info.get('addressRegion') or '',
        country=pycountry.countries.search_fuzzy(address_info.get('addressCountry'))[0].alpha_2,
        postal_code=address_info.get('postalCode') or '',
        delivery_instructions=address_info.get('deliveryInstructions') or '',
        address_type=db_address_type
    )
    return address


def update_address(address: Address, new_info: dict) -> Address:
    """Update address with new info."""
    address.street = new_info.get('streetAddress') or ''
    address.street_additional = new_info.get('streetAddressAdditional') or ''
    address.city = new_info.get('addressCity') or ''
    address.region = new_info.get('addressRegion') or ''
    address.country = pycountry.countries.search_fuzzy(new_info.get('addressCountry'))[0].alpha_2
    address.postal_code = new_info.get('postalCode') or ''
    address.delivery_instructions = new_info.get('deliveryInstructions') or ''

    return address


def create_office(business, office_type, addresses) -> Office:
    """Create a new office for incorporation."""
    office = Office()
    office.office_type = office_type
    office.addresses = []
    # Iterate addresses and add to this office
    for k, v in addresses.items():
        address = create_address(v, k)
        address.business_id = business.id
        if address:
            office.addresses.append(address)
    return office


def create_party(business_id: int, party_info: dict, create: bool = True) -> Party:
    """Create a new party or get them if they already exist."""
    party = None
    if not (middle_initial := party_info['officer'].get('middleInitial')):
        middle_initial = party_info['officer'].get('middleName', '')

    if create:
        party = PartyRole.find_party_by_name(
            business_id=business_id,
            first_name=party_info['officer'].get('firstName', '').upper(),
            last_name=party_info['officer'].get('lastName', '').upper(),
            middle_initial=middle_initial.upper(),
            org_name=party_info['officer'].get('organizationName', '').upper()
        )
    if not party:
        party = Party(
            first_name=party_info['officer'].get('firstName', '').upper(),
            last_name=party_info['officer'].get('lastName', '').upper(),
            middle_initial=middle_initial.upper(),
            title=party_info.get('title', '').upper(),
            organization_name=party_info['officer'].get('organizationName', '').upper(),
            email=party_info['officer'].get('email') or '',
            identifier=party_info['officer'].get('identifier') or '',
            party_type=party_info['officer'].get('partyType')
        )

    # add addresses to party
    if party_info.get('deliveryAddress', None):
        address = create_address(party_info['deliveryAddress'], Address.DELIVERY)
        party.delivery_address = address
    if party_info.get('mailingAddress', None):
        mailing_address = create_address(party_info['mailingAddress'], Address.MAILING)
        party.mailing_address = mailing_address
    return party


def create_role(party: Party, role_info: dict) -> PartyRole:
    """Create a new party role and link to party."""
    party_role = PartyRole(
        role=JSON_ROLE_CONVERTER.get(role_info.get('roleType').lower(), ''),
        appointment_date=role_info['appointmentDate'],
        cessation_date=role_info['cessationDate'],
        party=party
    )
    return party_role


def update_director(director: PartyRole, new_info: dict) -> PartyRole:
    """Update director with new info."""
    director.party.first_name = new_info['officer'].get('firstName', '').upper()
    director.party.middle_initial = new_info['officer'].get('middleInitial', '').upper()
    director.party.last_name = new_info['officer'].get('lastName', '').upper()
    director.party.title = new_info.get('title', '').upper()

    if director.party.delivery_address:
        director.party.delivery_address = update_address(
            director.party.delivery_address, new_info['deliveryAddress'])
    else:
        director.party.delivery_address = create_address(new_info['deliveryAddress'], Address.DELIVERY)

    if new_info.get('mailingAddress', None):
        if director.party.mailing_address is None:
            director.party.mailing_address = create_address(new_info['mailingAddress'], Address.MAILING)
        else:
            director.party.mailing_address = update_address(
                director.party.mailing_address, new_info['mailingAddress']
            )
    director.cessation_date = new_info.get('cessationDate')

    return director
