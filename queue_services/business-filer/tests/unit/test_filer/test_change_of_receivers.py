# Copyright © 2025 Province of British Columbia
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
"""The Test Suite to ensure that the worker is operating correctly for change of receivers."""
import copy
import datetime
from datetime import datetime, timezone
import random

from business_model.models import Address, Business, Filing, PartyRole, Party
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import (
    create_business,
    create_filing
)
from business_filer.common.filing_message import FilingMessage

CHANGE_OF_RECEIVERS_APPOINT = {
    'type': 'appointReceiver',
    'relationships': [
        {
            'entity': {
                'givenName': 'Phillip Tandy',
                'familyName': 'Miller',
                'alternateName': 'Phil Miller'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'Receiver'
                }
            ]
        },
        {
            'entity': {
                'businessName': 'Test Business',
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'roleType': 'Receiver'
                }
            ]
        },
        {
            'entity': {
                'givenName': 'Test',
                'middleInitial': 'T',
                'familyName': 'Tester',
                'alternateName': 'Testing'
            },
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'CA',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'roles': [
                {
                    'roleType': 'Receiver'
                }
            ]
        }
    ]
}


def test_process_cor_filing(app, session):
    """Assert that all COR filings can be applied to the model correctly."""
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    identifier = f'BC{random.randint(1000000, 9999999)}'


    business = create_business(identifier)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfReceivers'
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['changeOfReceivers'] = copy.deepcopy(CHANGE_OF_RECEIVERS_APPOINT)

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    appoint_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    assert appoint_filing.transaction_id
    assert appoint_filing.business_id == business.id
    assert appoint_filing.status == Filing.Status.COMPLETED.value

    party_roles: list[PartyRole] = business.party_roles.all()
    assert len(party_roles) == 3
    for role in party_roles:
        assert role.appointment_date
        assert not role.cessation_date
        assert role.role == PartyRole.RoleTypes.RECEIVER.value


    # Test cease receivers

    party_id_1 = party_roles[0].party_id
    party_id_2 = party_roles[1].party_id
    party_id_3 = party_roles[2].party_id

    filing['filing']['changeOfReceivers'] = {
        'type': 'ceaseReceiver',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_1
                },
                'roles': [
                    {
                        'roleType': PartyRole.RoleTypes.RECEIVER.value,
                        # NOTE: will be overriden by filing effective date
                        'cessationDate': '2025-03-04'
                    }
                ]
            }
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    cease_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    assert cease_filing.transaction_id
    assert cease_filing.business_id == business.id
    assert cease_filing.status == Filing.Status.COMPLETED.value

    party_roles: list[PartyRole] = business.party_roles.all()

    assert len(party_roles) == 3

    for role in party_roles:
        if role.party_id == party_id_1:
            assert role.cessation_date == cease_filing.effective_date
        else:
            assert role.party_id in [party_id_2, party_id_3]
            assert role.cessation_date is None
    
    # Test change address receivers

    new_address_delivery = {
        'streetAddress': 'Changed Delivery',
        'streetAddressAdditional': '',
        'addressCity': 'Vancouver',
        'addressRegion': 'BC',
        'addressCountry': 'CA',
        'postalCode': 'V0N4Y8',
        'deliveryInstructions': ''
    }
    new_address_mailing = {
        'streetAddress': 'Changed Mailing',
        'streetAddressAdditional': '',
        'addressCity': 'Vancouver',
        'addressRegion': 'BC',
        'addressCountry': 'CA',
        'postalCode': 'V0N4Y8',
        'deliveryInstructions': ''
    }
    filing['filing']['changeOfReceivers'] = {
        'type': 'changeAddressReceiver',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_2
                },
                'deliveryAddress': new_address_delivery,
                'mailingAddress': new_address_mailing
            }
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    change_address_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    assert change_address_filing.transaction_id
    assert change_address_filing.business_id == business.id
    assert change_address_filing.status == Filing.Status.COMPLETED.value

    party_roles: list[PartyRole] = business.party_roles.all()

    assert len(party_roles) == 3

    for role in party_roles:
        if role.party_id == party_id_2:
            delivery_address: Address = role.party.delivery_address
            mailing_address: Address = role.party.mailing_address
            assert delivery_address.address_type == 'delivery'
            assert delivery_address.street == new_address_delivery['streetAddress']
            assert mailing_address.address_type == 'mailing'
            assert mailing_address.street == new_address_mailing['streetAddress']
    
    
    # Test ammend receivers

    new_address_delivery_ammend = {
        'streetAddress': 'Changed Delivery ammend',
        'streetAddressAdditional': '',
        'addressCity': 'Vancouver',
        'addressRegion': 'BC',
        'addressCountry': 'CA',
        'postalCode': 'V0N4Y8',
        'deliveryInstructions': ''
    }
    new_name = {
        'givenName': 'Changed',
        'middleInitial': 'Tandy',
        'familyName': 'Miller',
        'alternateName': 'Phil Mills'
    }
    new_relationship = {
        'entity': {
            'givenName': 'New Guy',
            'familyName': 'Test'
        },
        'deliveryAddress': {
            'streetAddress': 'delivery_address - address line one',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'mailingAddress': {
            'streetAddress': 'mailing_address - address line one',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'roles': [
            {
                'roleType': 'Receiver'
            }
        ]
    }
    filing['filing']['changeOfReceivers'] = {
        'type': 'ammendReceiver',
        'relationships': [
            {
                'entity': {
                    'identifier': party_id_2,
                    'businessName': 'Test Business'
                },
                'deliveryAddress': new_address_delivery_ammend
            },
            {
                'entity': {
                    'identifier': party_id_3,
                    **new_name
                },
                'deliveryAddress': new_address_delivery_ammend
            },
            new_relationship
        ]
    }
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()
    
    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    ammend_filing: Filing = Filing.find_by_id(filing_rec.id)
    business: Business = Business.find_by_internal_id(business.id)

    # assert changes
    assert ammend_filing.transaction_id
    assert ammend_filing.business_id == business.id
    assert ammend_filing.status == Filing.Status.COMPLETED.value

    party_roles: list[PartyRole] = business.party_roles.all()

    assert len(party_roles) == 4

    for role in party_roles:
        party: Party = role.party
        delivery_address: Address = role.party.delivery_address
        mailing_address: Address = role.party.mailing_address
        if role.party_id == party_id_2:
            assert delivery_address.address_type == 'delivery'
            assert delivery_address.street == new_address_delivery_ammend['streetAddress']
            # mailing should be unchanged
            assert mailing_address.address_type == 'mailing'
            assert mailing_address.street == new_address_mailing['streetAddress']
        elif role.party_id == party_id_3:
            assert party.first_name == new_name['givenName'].upper()
            assert party.last_name == new_name['familyName'].upper()
            assert party.middle_initial == new_name['middleInitial'].upper()
            assert party.alternate_name == new_name['alternateName'].upper()
        elif role.party_id != party_id_1:
            # new relationship
            assert party.first_name == new_relationship['entity']['givenName'].upper()
            assert party.last_name == new_relationship['entity']['familyName'].upper()
            assert delivery_address.address_type == 'delivery'
            assert delivery_address.street == new_relationship['deliveryAddress']['streetAddress']
            assert mailing_address.address_type == 'mailing'
            assert mailing_address.street == new_relationship['mailingAddress']['streetAddress']