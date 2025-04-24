# Copyright © 2024 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Unit Tests and the helper routines."""
import copy

from tests import EPOCH_DATETIME
from business_model.models import Address, Business, Filing, Office, Party, PartyRole

def create_filing(token=None, json_filing=None, business_id=None,
                  filing_date=EPOCH_DATETIME, transaction_id: str = None):
    """Return a test filing."""
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
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    office = create_business_address()
    business.offices.append(office)
    return business


def create_business_address(office_type='businessOffice'):
    """Create an address."""
    office = Office(office_type=office_type)
    office.addresses.append(create_office(Address.DELIVERY))
    office.addresses.append(create_office(Address.MAILING))
    return office


def create_office(type):
    """Create an office."""
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
