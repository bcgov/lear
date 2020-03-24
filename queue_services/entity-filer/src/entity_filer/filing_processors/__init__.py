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
"""This module contains all of the Legal Filing specific processors.

Processors hold the business logic for how a filing is interpreted and saved to the legal database.
"""
from typing import Dict

import pycountry
from legal_api.models import Address, Business, Director, Office, Party, PartyRole


def create_address(address_info: Dict, address_type: str):
    """Create an address."""
    address = Address(street=address_info.get('streetAddress'),
                      street_additional=address_info.get('streetAddressAdditional'),
                      city=address_info.get('addressCity'),
                      region=address_info.get('addressRegion'),
                      country=pycountry.countries.search_fuzzy(address_info.get('addressCountry'))[0].alpha_2,
                      postal_code=address_info.get('postalCode'),
                      delivery_instructions=address_info.get('deliveryInstructions'),
                      address_type=address_type
                      )
    return address


def update_address(address: Address, new_info: dict):
    """Update address with new info."""
    address.street = new_info.get('streetAddress')
    address.street_additional = new_info.get('streetAddressAdditional')
    address.city = new_info.get('addressCity')
    address.region = new_info.get('addressRegion')
    address.country = pycountry.countries.search_fuzzy(new_info.get('addressCountry'))[0].alpha_2
    address.postal_code = new_info.get('postalCode')
    address.delivery_instructions = new_info.get('deliveryInstructions')

    return address


def create_director(director_info: dict):
    """Create a new party director role and create/link party."""
    # create person/organization get them if they already exist
    party = Party.find_by_name(
        first_name=director_info['officer'].get('firstName', '').upper(),
        last_name=director_info['officer'].get('lastName', '').upper(),
        organization_name=director_info.get('organization_name', '').upper()
    )
    if not party:
        party = Party(
            first_name=director_info['officer'].get('firstName', '').upper(),
            last_name=director_info['officer'].get('lastName', '').upper(),
            middle_initial=director_info['officer'].get('middleInitial', '').upper(),
            title=director_info.get('title', '').upper(),
            organization_name=director_info.get('organization_name', '').upper()
        )

    # add addresses to party
    address = create_address(director_info['deliveryAddress'], Address.DELIVERY)
    party.delivery_address = address
    if director_info.get('mailingAddress', None):
        mailing_address = create_address(director_info['mailingAddress'], Address.MAILING)
        party.mailing_address = mailing_address

    # create party role and link party to it
    party_role = PartyRole(
        role=PartyRole.RoleTypes.DIRECTOR.value,
        appointment_date=director_info.get('appointmentDate'),
        cessation_date=director_info.get('cessationDate'),
        party=party
    )
    return party_role


def update_director(director: Director, party_role: PartyRole, new_info: dict):
    """Update director with new info."""
    if director:
        director.first_name = new_info['officer'].get('firstName', '').upper()
        director.middle_initial = new_info['officer'].get('middleInitial', '').upper()
        director.last_name = new_info['officer'].get('lastName', '').upper()
        director.title = new_info.get('title', '').upper()
        # director.appointment_date = new_info.get('appointmentDate')
        director.cessation_date = new_info.get('cessationDate')
        director.delivery_address = update_address(director.delivery_address, new_info['deliveryAddress'])
        if 'mailingAddress' in new_info.keys():
            if director.mailing_address is None:
                director.mailing_address = create_address(new_info['mailingAddress'], Address.MAILING)
            else:
                director.mailing_address = update_address(director.mailing_address, new_info['mailingAddress'])

    if party_role:
        party_role.party.first_name = new_info['officer'].get('firstName', '').upper()
        party_role.party.middle_initial = new_info['officer'].get('middleInitial', '').upper()
        party_role.party.last_name = new_info['officer'].get('lastName', '').upper()
        party_role.party.title = new_info.get('title', '').upper()
        party_role.party.delivery_address = update_address(
            party_role.party.delivery_address, new_info['deliveryAddress'])
        if new_info.get('mailingAddress', None):
            if party_role.party.mailing_address is None:
                party_role.party.mailing_address = create_address(new_info['mailingAddress'], Address.MAILING)
            else:
                party_role.party.mailing_address = update_address(
                    party_role.party.mailing_address, new_info['mailingAddress']
                )
        party_role.cessation_date = new_info.get('cessationDate')
        return party_role

    return director


def create_office(business, office_type, addresses):
    """Create a new office for incorporation."""
    office = Office()
    office.business_id = business.id
    office.office_type = office_type
    office.addresses = []
    # Iterate addresses and add to this office
    for k, v in addresses.items():
        address = create_address(v, k)
        address.business_id = business.id
        if address:
            office.addresses.append(address)
    return office
