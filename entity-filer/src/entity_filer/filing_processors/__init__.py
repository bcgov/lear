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
import pycountry
from legal_api.models import Address, Director


def create_address(address_info, address_type):
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


def update_director(director: Director, new_info: dict):
    """Update director with new info."""
    director.first_name = new_info['officer'].get('firstName', '').upper()
    director.middle_initial = new_info['officer'].get('middleInitial', '').upper()
    director.last_name = new_info['officer'].get('lastName', '').upper()
    director.title = new_info.get('title', '').upper()
    # director.appointment_date = new_info.get('appointmentDate')
    director.cessation_date = new_info.get('cessationDate')
    director.delivery_address = update_address(director.delivery_address, new_info['deliveryAddress'])
    if ('mailingAddress' in new_info.keys()):
        if director.mailing_address == None:
            director.mailing_address = create_address(new_info['mailingAddress'], Address.MAILING)
        else:
            director.mailing_address = update_address(director.mailing_address, new_info['mailingAddress'])

    return director
