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
import json
import datetime
import pytest
from business_model.models import Business, Filing

from business_filer.filing_processors.filing_components.parties import update_parties


PARTIES_STRUCTURE = {
    'parties': [
        {
            'roles': [
                {
                    'roleType': 'Completing Party',
                    'appointmentDate': '2020-08-31'
                },
                {
                    'roleType': 'Incorporator',
                    'appointmentDate': '2020-08-31'
                },
                {
                    'roleType': 'Director',
                    'appointmentDate': '2020-08-31'
                }
            ],
            'officer': {
                'id': 0,
                'email': 'test@test.com',
                'organizationName': '',
                'lastName': 'Test',
                'firstName': 'Test',
                'partyType': 'person',
                'middleName': ''
            },
            'mailingAddress': {
                'postalCode': 'N2E 3J7',
                'addressCity': 'Kitchener',
                'addressRegion': 'ON',
                'streetAddress': '45-225 Country Hill Dr',
                'addressCountry': 'CA',
                'streetAddressAdditional': ''
            },
            'deliveryAddress': {
                'postalCode': 'N2E 3J7',
                'addressCity': 'Kitchener',
                'addressRegion': 'ON',
                'streetAddress': '45-225 Country Hill Dr',
                'addressCountry': 'CA',
                'streetAddressAdditional': ''
            }
        }
    ]
}

SECOND_PARTY = {
    'parties': [
        {
            'roles': [
                {
                    'roleType': 'Director',
                    'appointmentDate': '2020-08-31'
                }
            ],
            'officer': {
                'id': 1,
                'email': 'test@test.com',
                'organizationName': '',
                'lastName': 'Test abc',
                'firstName': 'Test abc',
                'partyType': 'person',
                'middleName': ''
            },
            'mailingAddress': {
                'postalCode': 'N2E 3J7',
                'addressCity': 'Kitchener',
                'addressRegion': 'ON',
                'streetAddress': '45-225 Country Hill Dr',
                'addressCountry': 'CA',
                'streetAddressAdditional': ''
            },
            'deliveryAddress': {
                'postalCode': 'N2E 3J7',
                'addressCity': 'Kitchener',
                'addressRegion': 'ON',
                'streetAddress': '45-225 Country Hill Dr',
                'addressCountry': 'CA',
                'streetAddressAdditional': ''
            }
        }
    ]
}


@pytest.mark.parametrize('test_name,parties_structure,expected_error', [
    ('valid parties', PARTIES_STRUCTURE, None)
])
def test_manage_parties_structure__parties(
        app, session,
        test_name, parties_structure, expected_error):
    """Assert that the parties and party roles gets set."""
    business = Business()
    business.save()

    data = {'filing': 'not a real filing, fail validation'}
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()
    assert filing.id is not None

    update_and_validate_party_and_roles(business, parties_structure, 1, 1, filing, 2)


@pytest.mark.parametrize('test_name,parties_structure,expected_error', [
    ('deletes and creates parties', PARTIES_STRUCTURE, None)
])
def test_manage_parties_structure__delete_and_recreate(app, session, test_name, parties_structure, expected_error):
    """Assert that the parties and party roles gets set."""
    business = Business()
    business.save()

    data = {'filing': 'not a real filing, fail validation'}
    filing1 = Filing()
    filing1.business_id = business.id
    filing1.filing_date = datetime.datetime.utcnow()
    filing1.filing_data = json.dumps(data)
    filing1.save()

    update_and_validate_party_and_roles(business, parties_structure, 1, 1, filing1, 2)

    filing2 = Filing()
    filing2.business_id = business.id
    filing2.filing_date = datetime.datetime.utcnow()
    filing2.filing_data = json.dumps(data)
    filing2.save()

    update_and_validate_party_and_roles(business, SECOND_PARTY, 1, 1, filing2, 0)


def update_and_validate_party_and_roles(business, parties_structure, roles_count, parties_count, filing,
                                        filing_parties_count):
    """Validate that party and party roles get created."""
    party_id_list = []
    err = update_parties(business, parties_structure['parties'], filing)
    business.save()
    check_business = Business.find_by_internal_id(business.id)
    check_party_roles = check_business.party_roles.all()
    for role in check_party_roles:
        if role.party_id not in party_id_list:
            party_id_list.append(role.party_id)
    assert len(check_party_roles) == roles_count
    assert len(party_id_list) == parties_count
    assert len(filing.filing_party_roles.all()) == filing_parties_count
    assert not err
