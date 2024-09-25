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
import copy

from tests import EPOCH_DATETIME


def create_filing(token=None, json_filing=None, business_id=None,
                  filing_date=EPOCH_DATETIME, transaction_id: str = None):
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
    if transaction_id:
        filing.transaction_id = transaction_id

    return filing


def create_business(identifier, legal_type=None, legal_name=None):
    """Return a test business."""
    from legal_api.models import Business
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    office = create_business_address()
    business.offices.append(office)
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


def create_registration_data(legal_type, identifier='FM1234567', tax_id=None, legal_name='test-reg-'):
    """Test data for registration."""
    person_json = {
        'officer': {
            'id': 2,
            'firstName': 'Peter',
            'lastName': 'Griffin',
            'middleName': '',
            'partyType': 'person'
        },
        'mailingAddress': {
            'streetAddress': 'mailing_address - address line one',
            'streetAddressAdditional': '',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }
    }

    org_json = copy.deepcopy(person_json)
    org_json['officer'] = {
        'id': 2,
        'organizationName': 'Xyz Inc.',
        'identifier': 'BC1234567',
        'taxId': '123456789',
        'email': 'peter@email.com',
        'partyType': 'organization'
    }

    business = create_business(identifier,
                               legal_type=legal_type,
                               legal_name=legal_name + legal_type)
    if tax_id:
        business.tax_id = tax_id

    json_filing = {
        'filing': {
            'header': {
                'name': 'registration'
            },
            'registration': {

            }
        }
    }
    filing = create_filing(json_filing=json_filing)
    party = create_party(person_json if legal_type == 'SP' else org_json)
    role = 'proprietor' if legal_type == 'SP' else 'partner'
    create_party_role(business, party, [role])

    business.save()
    filing.business_id = business.id
    filing.save()

    return filing.id, business.id
