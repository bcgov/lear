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

"""Tests to assure the business-incorporation logic.

Test-Suite to ensure that incorporation is working as expected.
"""
import copy
from http import HTTPStatus

from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from legal_api.models import Business
from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header


def test_post_new_incorporation(session, client, jwt):
    """Assert that an incorporation filing can be posted to businesses."""
    nr_number = 'NR1234567'
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    # Post initial filing
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['status'] == 'DRAFT'

    # verify business has actually been inserted
    business = Business.find_by_identifier(nr_number)

    assert business
    assert business.identifier == nr_number


def test_post_duplicate_incorporation(session, client, jwt):
    """Assert that only one incorporation filing can be created per NR number."""
    nr_number = 'NR1234567'
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number

    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.CREATED
    # Attempt a POST with the same NR
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['message'] == 'Incorporation filing for NR1234567 already exists'


def test_update_incorporation_filing(session, client, jwt):
    """Assert that incorporation filings can be edited/updated via businesses."""
    nr_number = 'NR1234567'
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    # Post initial filing
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['incorporationApplication']['contactPoint']['email'] == 'no_one@never.get'
    filing['filing']['incorporationApplication']['contactPoint']['email'] = 'some_one@never.get'
    # Update the incorporation filing
    rv = client.put(f'/api/v1/businesses/{nr_number}',
                    json=filing,
                    headers=create_header(jwt, [STAFF_ROLE], nr_number))
    # Ensure accepted response
    assert rv.status_code == HTTPStatus.ACCEPTED
    # Check that the change (the email address) has in fact been changed and returned in the response JSON
    assert rv.json['filing']['incorporationApplication']['contactPoint']['email'] == 'some_one@never.get'


def test_update_incorporation_mismatch(session, client, jwt):
    """Assert that an incorporation filing can be posted to businesses."""
    # Create two NR numbers
    nr_number = 'NR1234567'
    nr_bad_number = 'NR7654321'
    # Create two separate filings for incorporation
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    second_filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)

    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    second_filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_bad_number
    # Post initial filing
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.CREATED
    # Post second incorporation filing for second company
    rv = client.post(f'/api/v1/businesses',
                     json=second_filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_bad_number))

    assert rv.status_code == HTTPStatus.CREATED
    # Attempt to update NR-1 with the identifier from NR-2
    rv = client.put(f'/api/v1/businesses/{nr_bad_number}',
                    json=filing,
                    headers=create_header(jwt, [STAFF_ROLE], nr_bad_number))
    # Assert that validator does not allow mismatches
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json[0]['error'] == 'Business Identifier does not match the identifier in filing.'


def test_get_incorporation_filings(session, client, jwt):
    """Assert that an incorporation filing can be retrieved for resuming."""
    nr_number = 'NR1234567'
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    print(filing)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    # Post initial filing
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['filingId']
    filing_id = rv.json['filing']['header']['filingId']

    # Retrieve the incorporation filing
    rv = client.get(f'/api/v1/businesses/{nr_number}/filings/{filing_id}',
                    headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['header']['filingId'] == filing_id
