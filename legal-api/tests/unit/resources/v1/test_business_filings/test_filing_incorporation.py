# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the business-filing end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import copy
from http import HTTPStatus

from registry_schemas.example_data import FILING_TEMPLATE, INCORPORATION

from legal_api.models import Filing, LegalEntity, RegistrationBootstrap
from legal_api.services.authz import STAFF_ROLE, SYSTEM_ROLE
from tests import integration_affiliation, integration_payment
from tests.unit.services.utils import create_header


def setup_bootstrap_ia_minimal(jwt, session, client, account_id):
    """Render a minimal ia filing."""
    #
    # SETUP
    #
    filing = {'filing':
              {
                  'header':
                  {
                      'name': 'incorporationApplication',
                      'accountId': account_id
                  },
                  'incorporationApplication': {
                      'nameRequest': {
                          'legalType': LegalEntity.EntityTypes.BCOMP.value
                      }
                  }
              }
              }
    rv = client.post('/api/v1/businesses?draft=true',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    identifier = rv.json['filing']['business']['identifier']
    filing_id = rv.json['filing']['header']['filingId']
    return identifier, filing_id


@integration_affiliation
def test_get_bootstrap_draft_filing(client, jwt, session):
    """Assert that a draft IA filing can be retrieved."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)
    #
    # Test that we can get the filing
    #
    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                    headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['business']['identifier'] == identifier
    assert rv.json['filing']['header']['filingId'] == filing_id


@integration_affiliation
def test_delete_bootstrap_draft_filing(client, jwt, session):
    """Assert that a draft IA filing can be retrieved."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)
    #
    # Test that we can get the filing
    #
    rv = client.delete(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                       headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.OK
    assert not Filing.find_by_id(filing_id)
    assert not RegistrationBootstrap.find_by_identifier(identifier)


@integration_affiliation
def test_get_bootstrap_draft_wrong_filing(client, jwt, session):
    """Assert that an invalid filing cannot be found."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)
    #
    # Test that we can get the filing
    #
    filing_id += 1
    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                    headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.NOT_FOUND


@integration_affiliation
def test_get_bootstrap_draft_filing_iff_one_exists(client, jwt, session):
    """Assert that a draft IA filing can be retrieved, iff there's only one at the filing endpoint.."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)
    #
    # Test that we can get the filing
    #
    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['business']['identifier'] == identifier
    assert rv.json['filing']['header']['filingId'] == filing_id


@integration_affiliation
@integration_payment
def test_create_incorporation_success_filing(client, jwt, session):
    """Assert that a valid IA can be posted."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing'].pop('business')
    filing['filing']['business'] = {}
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    filing['filing']['header']['name'] = 'incorporationApplication'
    filing['filing']['header']['accountId'] = account_id

    # remove fed
    filing['filing']['header'].pop('effectiveDate')

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                    json=filing,
                    headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['header']['accountId'] == account_id
    assert rv.json['filing']['header']['name'] == 'incorporationApplication'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


@integration_affiliation
@integration_payment
def test_create_incorporation_success_filing_routing_slip(client, jwt, session):
    """Assert that a valid IA can be posted."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing'].pop('business')
    filing['filing']['business'] = {}
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    filing['filing']['header']['name'] = 'incorporationApplication'
    filing['filing']['header']['accountId'] = account_id
    filing['filing']['header']['routingSlipNumber'] = '111111111'

    # remove fed
    filing['filing']['header'].pop('effectiveDate')

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                    json=filing,
                    headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['header']['accountId'] == account_id
    assert rv.json['filing']['header']['name'] == 'incorporationApplication'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


@integration_affiliation
@integration_payment
def test_create_incorporation_with_bcol_dat(client, jwt, session):
    """Assert that a valid IA can be posted."""
    account_id = 26
    identifier, filing_id = setup_bootstrap_ia_minimal(jwt, session, client, account_id)

    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing'].pop('business')
    filing['filing']['business'] = {}
    filing['filing']['business']['identifier'] = identifier
    filing['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    filing['filing']['header']['name'] = 'incorporationApplication'
    filing['filing']['header']['accountId'] = account_id
    filing['filing']['header']['bcolAccountNumber'] = '180670'
    filing['filing']['header']['datNumber'] = 'C1234567'

    # remove fed
    filing['filing']['header'].pop('effectiveDate')

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filing_id}',
                    json=filing,
                    headers=create_header(jwt, [SYSTEM_ROLE], None))

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['header']['accountId'] == account_id
    assert rv.json['filing']['header']['name'] == 'incorporationApplication'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value
