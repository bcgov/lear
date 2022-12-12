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
"""Test Suite for all of the filing validations."""
from datetime import datetime, timedelta

def lists_are_equal(list_1, list_2) -> bool:
    """Assert that the unordered lists contain the same elements."""
    if len(list_1) != len(list_2):
        return False
    found = False
    for i in list_1:
        for j in list_2:
            if i == j:
                found = True
                break
            else:
                found = False
    return found


def create_party(roles: list,
                 party_id=None,
                 mailing_addr=None,
                 delivery_addr=None,
                 officer=None):
    """Create party object with custom roles, mailing addresses and delivery aadresses."""

    if officer:
        party = {
            'officer': officer,
            'mailingAddress': None,
            'deliveryAddress': None,
            'roles': []
        }
        if party_id:
            party.id = party_id
    else:
        party = {
            'officer': {
                'id': party_id,
                'firstName': 'Joe',
                'lastName': 'Swanson',
                'middleName': 'P',
                'email': 'joe@email.com',
                'organizationName': '',
                'partyType': 'person'
            },
            'mailingAddress': None,
            'deliveryAddress': None,
            'roles': []
        }

    for role in roles:
        party['roles'].append({
            'roleType': role,
            'appointmentDate': '2018-01-01'
        })

    if mailing_addr:
        party['mailingAddress'] = mailing_addr

    if mailing_addr:
        party['deliveryAddress'] = delivery_addr

    return party


def create_party_address(base_address=None,
                         street=None,
                         street_additional=None,
                         city=None,
                         country=None,
                         postal_code=None,
                         region=None):
    """Create party address with option to provide base address and override properties as necessary."""
    if base_address:
        party_address = base_address
        party_address['streetAddress'] = street if street is not None else party_address['streetAddress']
        party_address['streetAddressAdditional'] = street_additional \
            if street_additional is not None else party_address['streetAddressAdditional']
        party_address['addressCity'] = city if city is not None else party_address['addressCity']
        party_address['addressCountry'] = country if country is not None else party_address['addressCountry']
        party_address['postalCode'] = postal_code if postal_code is not None else party_address['postalCode']
        party_address['addressRegion'] = region if region is not None else party_address['addressRegion']
    else:
        return {
               'streetAddress': street,
               'streetAddressAdditional': street_additional,
               'addressCity': city,
               'addressCountry': country,
               'postalCode': postal_code,
               'addressRegion': region
           }

    return party_address


def create_officer(base_officer=None,
                   first_name=None,
                   middle_name=None,
                   last_name=None,
                   organization_name=None,
                   party_type=None):
    if base_officer:
        officer = base_officer
        base_officer['firstName'] = first_name if first_name is not None else officer['firstName']
        base_officer['middleName'] = middle_name if middle_name is not None else officer['middleName']
        base_officer['lastName'] = last_name if last_name is not None else officer['lastName']
        base_officer['organizationName'] = organization_name if organization_name is not None \
                                            else officer['organizationName']
        base_officer['partyType'] = party_type if party_type is not None else officer['partyType']
        return officer
    else:
        return {
            'firstName': first_name,
            'middleName': middle_name,
            'lastName': last_name,
            'organizationName': organization_name,
            'partyType': party_type
        }


def create_utc_future_date_str(days: int):
    """Create a future utc date and return as string."""
    now = datetime.utcnow().date()
    td = timedelta(days=days)
    result = (now + td).strftime('%Y-%m-%d')
    return result
