# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the business filing component processors."""
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
    business = Business()
    business.save()
    update_and_validate_office(business, office_structure)


@pytest.mark.parametrize('test_name,office_structure,expected_error', [
    ('delete and recreate office', OFFICE_STRUCTURE, None)
])
def test_manage_office_structure__delete_and_recreate_offices(app, session, test_name, office_structure,
                                                              expected_error):
    """Assert that the corp offices gets deleted and recreated."""
    business = Business()
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
