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
from legal_api.models import Address


def create_address(address_info, address_type):
    """Create an address."""
    address = Address(street=address_info.get('streetAddress'),
                      street_additional=address_info.get('streetAddressAdditional'),
                      city=address_info.get('addressCity'),
                      region=address_info.get('addressRegion'),
                      country=address_info.get('addressCountry'),
                      postal_code=address_info.get('postalCode'),
                      delivery_instructions=address_info.get('deliveryInstructions'),
                      address_type=address_type
                      )
    return address


def update_address(address: Address, new_info: dict, ):
    address.street = new_info.get('streetAddress')
    address.street_additional = new_info.get('streetAddressAdditional')
    address.city = new_info.get('addressCity')
    address.region = new_info.get('addressRegion')
    address.country = new_info.get('addressCountry')
    address.postal_code = new_info.get('postalCode')
    address.delivery_instructions = new_info.get('deliveryInstructions')

    return address
