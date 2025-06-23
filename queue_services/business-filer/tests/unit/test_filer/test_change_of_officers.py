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
"""The Test Suites to ensure that the worker is operating correctly."""
import copy
import datetime
from datetime import datetime, timezone
import random
from sqlalchemy import select

from business_model.models import Business, Filing, PartyRole, Party, Address
from registry_schemas.example_data import FILING_TEMPLATE

from business_filer.services.filer import process_filing
from tests.unit import (
    create_business,
    create_filing
)
from business_filer.common.filing_message import FilingMessage

CHANGE_OF_OFFICERS = {
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
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'Chair',
                    'roleClass': 'OFFICER'
                }
            ]
        },
        {
            'entity': {
                'givenName': 'Phillip Stacy',
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
                    'roleType': 'President',
                    'roleClass': 'OFFICER'
                },
                {
                    'appointmentDate': '2018-01-01',
                    'roleType': 'CEO',
                    'roleClass': 'OFFICER'
                }
            ]
        }
    ]
}

def test_process_coo_filing(app, session):
    """Assert that a COO filing can be applied to the model correctly."""
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    effective_date = datetime(2023, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    identifier = f'BC{random.randint(1000000, 9999999)}'


    business = create_business(identifier)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing']['header']['name'] = 'changeOfOfficers'
    filing['filing']['header']['effectiveDate'] = effective_date.isoformat()
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['business']['legalType'] = 'BC'
    filing['filing']['changeOfOfficers'] = CHANGE_OF_OFFICERS

    filing_rec = create_filing(payment_id, filing, business.id)
    filing_rec.effective_date = effective_date
    filing_rec.save()

    # setup
    filing_msg = FilingMessage(filing_identifier=filing_rec.id)

    # TEST
    process_filing(filing_msg)

    # Get modified data
    filing = Filing.find_by_id(filing_rec.id)
    business = Business.find_by_internal_id(business.id)

    # assert changes
    assert filing.transaction_id
    assert filing.business_id == business.id
    assert filing.status == Filing.Status.COMPLETED.value

    party_roles = business.party_roles.all()

    assert len(party_roles) == 4
