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
from datetime import date
from http import HTTPStatus

from freezegun import freeze_time
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from legal_api.models import Business, Filing
from legal_api.services.authz import STAFF_ROLE
from tests import integration_payment
from tests.unit.services.utils import create_header


# Setup
now = date(2020, 9, 17)
nr_number = 'NR 1234567'
effective_date = '2020-09-18T00:00:00+00:00'


def test_post_new_draft_incorporation(session, client, jwt):
    """Assert that an incorporation filing can be posted to businesses."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    filing['filing']['header']['effectiveDate'] = effective_date

    # perform test
    with freeze_time(now):
        # Post initial filing
        rv = client.post(f'/api/v1/businesses?draft=true',
                         json=filing,
                         headers=create_header(jwt, [STAFF_ROLE], nr_number))

        assert HTTPStatus.CREATED == rv.status_code
        assert 'DRAFT' == rv.json['filing']['header']['status']

        # verify business has actually been inserted with NR as identifier
        business = Business.find_by_identifier(nr_number)
        assert business


@integration_payment
def test_post_new_incorporation(session, client, jwt):
    """Assert that an incorporation filing can be posted to businesses and completed."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['header']['routingSlipNumber'] = '111111111'
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number

    # Post initial filing
    rv = client.post(f'/api/v1/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert HTTPStatus.CREATED == rv.status_code
    assert 'PENDING' == rv.json['filing']['header']['status']
    assert rv.json['filing']['header']['paymentToken'] is not None


def test_post_duplicate_incorporation(session, client, jwt):
    """Assert that only one incorporation filing can be created per NR number."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    filing['filing']['header']['effectiveDate'] = effective_date

    # perform test
    with freeze_time(now):
        rv = client.post(f'/api/v1/businesses?draft=true',
                         json=filing,
                         headers=create_header(jwt, [STAFF_ROLE], nr_number))

        assert rv.status_code == HTTPStatus.CREATED
        # Attempt a POST with the same NR
        rv = client.post(f'/api/v1/businesses',
                         json=filing,
                         headers=create_header(jwt, [STAFF_ROLE], nr_number))

        assert HTTPStatus.BAD_REQUEST == rv.status_code
        assert 'Incorporation filing for NR 1234567 already exists' == rv.json['errors'][0]['message']


def test_get_incorporation_filing(session, client, jwt):
    """Assert that an incorporation filing can be retrieved for resuming."""
    filing = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number
    filing['filing']['header']['effectiveDate'] = effective_date

    # perform test
    with freeze_time(now):
        # Post initial filing
        rv = client.post(f'/api/v1/businesses?draft=true',
                         json=filing,
                         headers=create_header(jwt, [STAFF_ROLE], nr_number))

        assert HTTPStatus.CREATED == rv.status_code
        assert rv.json['filing']['header']['filingId']

        filing_id = rv.json['filing']['header']['filingId']

        # Retrieve the incorporation filing
        rv = client.get(f'/api/v1/businesses/{nr_number}/filings/{filing_id}',
                        headers=create_header(jwt, [STAFF_ROLE], nr_number))

        assert HTTPStatus.OK == rv.status_code
        assert filing_id == rv.json['filing']['header']['filingId']


def test_put_draft_incorporation_filing(session, client, jwt):
    """Assert that an incorporation filing can be put (updated) to filings endpoint."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number

    business = Business()
    business.identifier = nr_number
    business.save()

    filing = Filing()
    filing.filing_json = filing_json
    filing.business_id = business.id
    filing.save()

    # PUT updated filing
    rv = client.put(f'/api/v1/businesses/{nr_number}/filings/{filing.id}?draft=true',
                    json=filing_json,
                    headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert HTTPStatus.ACCEPTED == rv.status_code


def test_put_incorporation_to_business_fails(session, client, jwt):
    """Assert that an incorporation cannot be PUT to the business endpoint."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number

    business = Business()
    business.identifier = nr_number
    business.save()

    filing = Filing()
    filing.filing_json = filing_json
    filing.business_id = business.id
    filing.save()

    # Post initial filing
    rv = client.put(f'/api/v1/businesses/{nr_number}',
                    json=filing_json,
                    headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert HTTPStatus.METHOD_NOT_ALLOWED == rv.status_code


def test_post_incorporation_to_filing_fails(session, client, jwt):
    """Assert that an incorporation cannot be POSTed to the filings endpoint."""
    filing_json = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_json['filing']['incorporationApplication']['nameRequest']['nrNumber'] = nr_number

    # Post initial filing
    rv = client.post(f'/api/v1/businesses/{nr_number}/filings/',
                     json=filing_json,
                     headers=create_header(jwt, [STAFF_ROLE], nr_number))

    assert HTTPStatus.NOT_FOUND == rv.status_code
