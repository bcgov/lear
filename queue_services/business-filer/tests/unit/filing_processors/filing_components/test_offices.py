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
"""The Unit Tests for the business filing component processors."""
import random

import pytest
from business_model.models import Business

from business_filer.filing_processors.filing_components.offices import update_offices
from tests import strip_keys_from_dict


OFFICE_STRUCTURE = {
    'offices': {
        'recordsOffice': {
            'mailingAddress': {
                'postalCode': 'L6M 4M6',
                'addressCity': 'Oakville',
                'addressRegion': 'BC',
                'streetAddress': '23-1489 Heritage Way',
                'addressCountry': 'CA',
                'deliveryInstructions': '',
                'streetAddressAdditional': ''
            },
            'deliveryAddress': {
                'postalCode': 'L6M 4M6',
                'addressCity': 'Oakville',
                'addressRegion': 'BC',
                'streetAddress': '23-1489 Heritage Way',
                'addressCountry': 'CA',
                'deliveryInstructions': '',
                'streetAddressAdditional': ''
            }
        },
        'registeredOffice': {
            'mailingAddress': {
                'postalCode': 'L6M 4M6',
                'addressCity': 'Oakville',
                'addressRegion': 'BC',
                'streetAddress': '23-1489 Heritage Way',
                'addressCountry': 'CA',
                'deliveryInstructions': '',
                'streetAddressAdditional': ''
            },
            'deliveryAddress': {
                'postalCode': 'L6M 4M6',
                'addressCity': 'Oakville',
                'addressRegion': 'BC',
                'streetAddress': '23-1489 Heritage Way',
                'addressCountry': 'CA',
                'deliveryInstructions': '',
                'streetAddressAdditional': ''
            }
        }
    }
}


@pytest.mark.parametrize('test_name,office_structure,expected_error', [
    ('valid office', OFFICE_STRUCTURE, None)
])
def test_manage_office_structure__offices(
        app, session,
        test_name, office_structure, expected_error):
    """Assert that the corp offices gets set."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = Business(identifier=identifier)
    business.save()
    update_and_validate_office(business, office_structure)


@pytest.mark.parametrize('test_name,office_structure,expected_error', [
    ('delete and recreate office', OFFICE_STRUCTURE, None)
])
def test_manage_office_structure__delete_and_recreate_offices(app, session, test_name, office_structure,
                                                              expected_error):
    """Assert that the corp offices gets deleted and recreated."""
    identifier = f'BC{random.randint(1000000, 9999999)}'
    business = Business(identifier=identifier)
    business.save()

    update_and_validate_office(business, office_structure)
    # Change the value of address to recreate
    office_structure['offices']['recordsOffice']['mailingAddress']['postalCode'] = 'L6M 5M7'
    update_and_validate_office(business, office_structure)


def update_and_validate_office(business, office_structure):
    """Validate that office gets created."""
    err = update_offices(business, office_structure['offices'])
    business.save()
    check_business = Business.find_by_internal_id(business.id)
    check_offices = check_business.offices.all()
    assert len(check_offices) == 2
    check_office_structure = {'offices': {}}
    for s in check_offices:
        check_office_structure['offices'][s.office_type] = {}
        for address in s.addresses:
            check_office_structure['offices'][s.office_type][f'{address.address_type}Address'] = address.json
    stripped_dict = strip_keys_from_dict(check_office_structure, ['id', 'addressType'])
    assert stripped_dict == office_structure
    assert not err
