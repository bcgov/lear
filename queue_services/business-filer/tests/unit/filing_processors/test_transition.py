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
"""The Unit Tests for the Transition filing."""

import copy
import datetime
import random

from business_model.models import Filing, PartyRole
from registry_schemas.example_data import TRANSITION_FILING_TEMPLATE

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import transition
from tests.unit import create_business, create_filing, create_party, create_party_role


def test_transition_filing_process(app, session):
    """Assert that the transition object is correctly populated to model objects."""
    # setup
    identifier = f'CP{random.randint(1000000,9999999)}'
    filing = copy.deepcopy(TRANSITION_FILING_TEMPLATE)
    filing['filing']['business']['identifier'] = identifier

    business = create_business(filing['filing']['business']['identifier'])
    
    base_address = {
        'streetAddressAdditional': '',
        'streetAddress': 'Original street',
        'addressCity': 'Vancouver',
        'addressRegion': 'BC',
        'addressCountry': 'CA',
        'postalCode': 'V0N4Y8',
        'deliveryInstructions': ''
    }
    party_json = {
        'officer': {
            'firstName': 'Test',
            'lastName': 'Tester',
        },
        'mailingAddress': base_address,
        'deliveryAddress': base_address
    }
    party = create_party(party_json)
    create_party_role(business, party, [PartyRole.RoleTypes.DIRECTOR.value], business.founding_date.date().isoformat())
    business.save()
    
    relationship = filing['filing']['transition']['relationships'][0]
    relationship['entity']['identifier'] = str(party.id)
    new_address_delivery = {**base_address, 'streetAddress': 'Changed Delivery'}
    new_address_mailing  = {**base_address, 'streetAddress': 'Changed Mailing'}
    relationship['deliveryAddress'] = new_address_delivery
    relationship['mailingAddress'] = new_address_mailing

    filing['filing']['transition']['relationships'] = [relationship]

    create_filing('abc', filing, business.id)

    effective_date = datetime.datetime.now(datetime.timezone.utc)
    filing_rec = Filing(effective_date=effective_date, filing_json=filing)
    filing_meta = FilingMeta(application_date=effective_date)

    # test
    transition.process(business, filing_rec, filing['filing'], filing_meta)

    # Assertions
    assert business.restriction_ind is False
    assert len(business.share_classes.all()) == len(filing['filing']['transition']['shareStructure']['shareClasses'])
    assert len(business.offices.all()) == len(filing['filing']['transition']['offices'])
    assert len(business.aliases.all()) == len(filing['filing']['transition']['nameTranslations'])
    assert len(business.party_roles.all()) == 1
    # currently no completing party in the form
    assert len(filing_rec.filing_party_roles.all()) == 0
    assert business.party_roles[0].party_id == party.id
    assert party.delivery_address.json['streetAddress'] == new_address_delivery['streetAddress']
    assert party.mailing_address.json['streetAddress'] == new_address_mailing['streetAddress']
