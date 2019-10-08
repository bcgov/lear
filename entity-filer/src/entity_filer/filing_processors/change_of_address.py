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
import json

from legal_api.models import Business, Filing

from entity_filer.filing_processors import update_address


def process(business: Business, filing: Filing):
    """Render the change_of_address onto the business model objects."""
    offices_array = json.dumps(filing['changeOfAddress']['offices'])
    # Only retrieve the offices component from the filing json
    offices = json.loads(offices_array)

    for item in offices.keys():
        office = business.offices.filter_by(office_type=item).one_or_none()
        for k, new_address in offices[item].items():
            k = k.replace('Address', '')
            address = office.addresses.filter_by(address_type=k).one_or_none()
            update_address(address, new_address)
