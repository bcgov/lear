# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests and the helper routines."""
from tests import EPOCH_DATETIME


def create_filing(token=None, json_filing=None, business_id=None, filing_date=EPOCH_DATETIME, bootstrap_id: str = None):
    """Return a test filing."""
    from legal_api.models import Filing
    filing = Filing()
    filing.filing_date = filing_date

    if token:
        filing.payment_token = str(token)
    if json_filing:
        filing.filing_json = json_filing
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def create_business(identifier, legal_type=None, legal_name=None):
    """Return a test business."""
    from legal_api.models import Address, Business
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    office = create_business_address()
    business.offices.append(office)
    business.save()
    return business


def create_business_address(office_type='businessOffice'):
    """Create an address."""
    from legal_api.models import Address, Office
    office = Office(office_type=office_type)
    office.addresses.append(create_office(Address.DELIVERY))
    office.addresses.append(create_office(Address.MAILING))
    return office


def create_office(type):
    """Create an office."""
    from legal_api.models import Address
    address = Address(
        city='Test City',
        street='Test Street',
        postal_code='T3S3T3',
        country='CA',
        region='BC',
        address_type=type
    )
    return address


def create_party(party_json):
    """Create a party."""
    from legal_api.models import Address, Party
    new_party = Party(
        first_name=party_json['officer'].get('firstName', '').upper(),
        last_name=party_json['officer'].get('lastName', '').upper(),
        middle_initial=party_json['officer'].get('middleInitial', '').upper(),
        title=party_json.get('title', '').upper(),
        organization_name=party_json['officer'].get('organizationName', '').upper(),
        email=party_json['officer'].get('email'),
        identifier=party_json['officer'].get('identifier'),
        tax_id=party_json['officer'].get('taxId'),
        party_type=party_json['officer'].get('partyType')
    )
    if party_json.get('mailingAddress'):
        mailing_address = Address(
            street=party_json['mailingAddress']['streetAddress'],
            city=party_json['mailingAddress']['addressCity'],
            country='CA',
            postal_code=party_json['mailingAddress']['postalCode'],
            region=party_json['mailingAddress']['addressRegion'],
            delivery_instructions=party_json['mailingAddress'].get('deliveryInstructions', '').upper()
        )
        new_party.mailing_address = mailing_address
    if party_json.get('deliveryAddress'):
        delivery_address = Address(
            street=party_json['deliveryAddress']['streetAddress'],
            city=party_json['deliveryAddress']['addressCity'],
            country='CA',
            postal_code=party_json['deliveryAddress']['postalCode'],
            region=party_json['deliveryAddress']['addressRegion'],
            delivery_instructions=party_json['deliveryAddress'].get('deliveryInstructions', '').upper()
        )
        new_party.delivery_address = delivery_address
    return new_party


def create_party_role(business, party, roles, appointment_date=EPOCH_DATETIME):
    """Create party roles."""
    from legal_api.models import PartyRole
    for role in roles:
        party_role = PartyRole(
            role=role,
            party=party,
            appointment_date=appointment_date,
            cessation_date=None
        )
        business.party_roles.append(party_role)
