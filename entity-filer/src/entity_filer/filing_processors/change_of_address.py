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
"""File processing rules and actions for the change of address."""
from legal_api.models import Address, Business, Filing


def process(business: Business, filing: Filing):
    """Render the change_of_address onto the business model objects."""
    address = filing['changeOfAddress'].get('deliveryAddress')
    delivery_address = Address(street=address.get('streetAddress'),
                               street_additional=address.get('streetAddressAdditional'),
                               city=address.get('addressCity'),
                               region=address.get('addressRegion'),
                               country=address.get('addressCountry'),
                               postal_code=address.get('postalCode'),
                               delivery_instructions=address.get('deliveryInstructions'),
                               address_type=Address.DELIVERY)
    business.delivery_address.append(delivery_address)

    address = filing['changeOfAddress'].get('mailingAddress')
    mailing_address = Address(street=address.get('streetAddress'),
                              street_additional=address.get('streetAddressAdditional'),
                              city=address.get('addressCity'),
                              region=address.get('addressRegion'),
                              country=address.get('addressCountry'),
                              postal_code=address.get('postalCode'),
                              delivery_instructions=address.get('deliveryInstructions'),
                              address_type=Address.MAILING)
    business.mailing_address.append(mailing_address)
