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
"""The Unit Tests for the Registrars Notation filing."""
import copy
import random
from datetime import datetime, timezone, timezone

from business_model.models import Business, Filing, Office, OfficeType
from registry_schemas.example_data import PUT_BACK_ON, FILING_HEADER

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors import put_back_on
from tests.unit import (
    create_business,
    create_filing,
    create_office,
    create_office_address,
    create_party,
    create_party_role,
)


def tests_filer_put_back_on(app, session):
    """Assert that the put back on object is correctly populated to model objects."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = create_business(identifier, legal_type='BC')

    party1 = create_party({
        'officer': {
            'firstName': '',
            'lastName': '',
            'middleName': '',
            'organizationName': 'Xyz some super super super super super super long business 12345678 name Inc.',
            'partyType': 'organization'
        },
        'mailingAddress': {
            'streetAddress': 'mailing_address - address line one',
            'streetAddressAdditional': '',
            'addressCity': 'mailing_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        },
        'deliveryAddress': {
            'streetAddress': 'delivery_address - address line one',
            'streetAddressAdditional': '',
            'addressCity': 'delivery_address city',
            'addressCountry': 'CA',
            'postalCode': 'H0H0H0',
            'addressRegion': 'BC'
        }
    })

    create_party_role(business, party1, ['custodian'], datetime.now(timezone.utc))
    business.save()

    office = create_office(business, 'custodialOffice')
    create_office_address(business, office, 'delivery')
    create_office_address(business, office, 'mailing')

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['putBackOn'] = copy.deepcopy(PUT_BACK_ON)

    filing_meta = FilingMeta()
    filing = create_filing('123', filing_json)
    filing_id = filing.id

    # Test
    put_back_on.process(business, filing_json['filing'], filing, filing_meta)
    business.save()

    # Check outcome
    # final_filing = Filing.find_by_id(filing_id)

    assert business.state == Business.State.ACTIVE
    assert business.state_filing_id == filing_id
    assert business.dissolution_date is None

    custodial_office = session.query(Office). \
        filter(Office.business_id == business.id). \
        filter(Office.office_type == OfficeType.CUSTODIAL). \
        one_or_none()
    assert not custodial_office

    party_roles = business.party_roles.all()
    assert len(party_roles) == 1
    custodian = party_roles[0]
    assert custodian.role == 'custodian'
    assert custodian.cessation_date
