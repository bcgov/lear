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
from __future__ import annotations

from typing import Dict

import pycountry
from legal_api.models import Address, Business, Office, Party, PartyRole, ShareClass, ShareSeries


JSON_ROLE_CONVERTER = {
    'Director': PartyRole.RoleTypes.DIRECTOR.value,
    'Incorporator': PartyRole.RoleTypes.INCORPORATOR.value,
    'Completing Party': PartyRole.RoleTypes.COMPLETING_PARTY.value
}


def create_address(address_info: Dict, address_type: str) -> Address:
    """Create an address."""
    if not address_info:
        return Address()
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


def update_address(address: Address, new_info: dict) -> Address:
    """Update address with new info."""
    address.street = new_info.get('streetAddress')
    address.street_additional = new_info.get('streetAddressAdditional')
    address.city = new_info.get('addressCity')
    address.region = new_info.get('addressRegion')
    address.country = pycountry.countries.search_fuzzy(new_info.get('addressCountry'))[0].alpha_2
    address.postal_code = new_info.get('postalCode')
    address.delivery_instructions = new_info.get('deliveryInstructions')

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


def create_party(business_id: int, party_info: dict) -> Party:
    """Create a new party or get them if they already exist."""
    party = PartyRole.find_party_by_name(
        business_id=business_id,
        first_name=party_info['officer'].get('firstName', '').upper(),
        last_name=party_info['officer'].get('lastName', '').upper(),
        middle_initial=party_info['officer'].get('middleInitial', '').upper(),
        org_name=party_info.get('orgName', '').upper()
    )
    if not party:
        party = Party(
            first_name=party_info['officer'].get('firstName', '').upper(),
            last_name=party_info['officer'].get('lastName', '').upper(),
            middle_initial=party_info['officer'].get('middleInitial', '').upper(),
            title=party_info.get('title', '').upper(),
            organization_name=party_info.get('orgName', '').upper()
        )

    # add addresses to party
    address = create_address(party_info.get('deliveryAddress', None), Address.DELIVERY)
    party.delivery_address = address
    if party_info.get('mailingAddress', None):
        mailing_address = create_address(party_info['mailingAddress'], Address.MAILING)
        party.mailing_address = mailing_address
    return party


def create_role(party: Party, role_info: dict) -> PartyRole:
    """Create a new party role and link to party."""
    party_role = PartyRole(
        role=JSON_ROLE_CONVERTER.get(role_info['roleType'], None),
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
    director.party.delivery_address = update_address(
        director.party.delivery_address, new_info['deliveryAddress'])
    if new_info.get('mailingAddress', None):
        if director.party.mailing_address is None:
            director.party.mailing_address = create_address(new_info['mailingAddress'], Address.MAILING)
        else:
            director.party.mailing_address = update_address(
                director.party.mailing_address, new_info['mailingAddress']
            )
    director.cessation_date = new_info.get('cessationDate')

    return director


def create_share_class(share_class_info: dict) -> ShareClass:
    """Create a new share class and associated series."""
    share_class = ShareClass(
        name=share_class_info['name'],
        priority=share_class_info['priority'],
        max_share_flag=share_class_info['hasMaximumShares'],
        max_shares=share_class_info.get('maxNumberOfShares', None),
        par_value_flag=share_class_info['hasParValue'],
        par_value=share_class_info.get('parValue', None),
        currency=share_class_info.get('currency', None),
        special_rights_flag=share_class_info['hasRightsOrRestrictions']
    )
    for series in share_class.series:
        share_series = ShareSeries(
            name=series['name'],
            priority=series['priority'],
            max_share_flag=series['hasMaximumShares'],
            max_shares=series.get('maxNumberOfShares', None),
            special_rights_flag=series['hasRightsOrRestrictions']
        )
        share_class.series.append(share_series)

    return share_class
