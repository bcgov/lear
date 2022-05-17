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

"""Tests to assure the business end-point.

Test-Suite to ensure that the /businesses endpoint is working as expected.
"""
import copy
from http import HTTPStatus
import pytest

import registry_schemas
from registry_schemas.example_data import FILING_TEMPLATE, INCORPORATION

from legal_api.models import Business, Filing
from legal_api.services.authz import STAFF_ROLE
from legal_api.utils.datetime import datetime
from tests import integration_affiliation
from tests.unit.models import factory_business
from tests.unit.services.compliance.compliance_checks import create_business
from tests.unit.services.utils import create_header


def factory_business_model(legal_name,
                           identifier,
                           founding_date,
                           last_ledger_timestamp,
                           last_modified,
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None):
    """Return a valid Business object stamped with the supplied designation."""
    from legal_api.models import Business as BusinessModel
    b = BusinessModel(legal_name=legal_name,
                      identifier=identifier,
                      founding_date=founding_date,
                      last_ledger_timestamp=last_ledger_timestamp,
                      last_modified=last_modified,
                      fiscal_year_end_date=fiscal_year_end_date,
                      dissolution_date=dissolution_date,
                      tax_id=tax_id
                      )
    b.save()
    return b


def test_create_bootstrap_failure_filing(client, jwt):
    """Assert the an empty filing cannot be used to bootstrap a filing."""
    filing = None
    rv = client.post('/api/v2/businesses?draft=true',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.BAD_REQUEST


@integration_affiliation
@pytest.mark.parametrize('filing_name', [
    'incorporationApplication',
    'registration'
])
def test_create_bootstrap_minimal_draft_filing(client, jwt, filing_name):
    """Assert that a minimal filing can be used to create a draft filing."""
    filing = {'filing':
              {
                  'header':
                  {
                      'name': filing_name,
                      'accountId': 28
                  }
              }
              }
    rv = client.post('/api/v2/businesses?draft=true',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['business']['identifier']
    assert rv.json['filing']['header']['accountId'] == 28
    assert rv.json['filing']['header']['name'] == filing_name


@integration_affiliation
def test_create_bootstrap_validate_success_filing(client, jwt):
    """Assert that a valid IA can be validated."""
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing'].pop('business')
    filing['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    filing['filing']['header']['name'] = 'incorporationApplication'
    filing['filing']['header']['accountId'] = 28

    # remove fed
    filing['filing']['header'].pop('effectiveDate')

    rv = client.post('/api/v2/businesses?only_validate=true',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['header']['accountId'] == 28
    assert rv.json['filing']['header']['name'] == 'incorporationApplication'


@integration_affiliation
def test_create_incorporation_success_filing(client, jwt, session):
    """Assert that a valid IA can be posted."""
    filing = copy.deepcopy(FILING_TEMPLATE)
    filing['filing'].pop('business')
    filing['filing']['incorporationApplication'] = copy.deepcopy(INCORPORATION)
    filing['filing']['header']['name'] = 'incorporationApplication'
    filing['filing']['header']['accountId'] = 28
    filing['filing']['header']['routingSlipNumber'] = '111111111'

    # remove fed
    filing['filing']['header'].pop('effectiveDate')

    rv = client.post('/api/v2/businesses',
                     json=filing,
                     headers=create_header(jwt, [STAFF_ROLE], None))

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json['filing']['header']['accountId'] == 28
    assert rv.json['filing']['header']['name'] == 'incorporationApplication'

    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def test_get_temp_business_info(session, client, jwt):
    """Assert that temp registration returns 200."""
    identifier = 'T7654321'

    rv = client.get('/api/v2/businesses/' + identifier,
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK


def test_get_business_info(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    legal_name = identifier + ' legal name'
    factory_business_model(legal_name=legal_name,
                           identifier=identifier,
                           founding_date=datetime.utcfromtimestamp(0),
                           last_ledger_timestamp=datetime.utcfromtimestamp(0),
                           last_modified=datetime.utcfromtimestamp(0),
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None)

    rv = client.get('/api/v2/businesses/' + identifier,
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    print('business json', rv.json)

    assert rv.json['business']['identifier'] == identifier

    print('valid schema?', registry_schemas.validate(rv.json, 'business'))

    assert registry_schemas.validate(rv.json, 'business')


def test_get_business_info_dissolution(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP1234567'
    legal_name = identifier + ' legal name'
    factory_business_model(legal_name=legal_name,
                           identifier=identifier,
                           founding_date=datetime.utcfromtimestamp(0),
                           last_ledger_timestamp=datetime.utcfromtimestamp(0),
                           last_modified=datetime.utcfromtimestamp(0),
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=datetime.utcfromtimestamp(0))
    rv = client.get(f'/api/v2/businesses/{identifier}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    # dissolved company cannot be found.
    assert rv.status_code == 200
    assert rv.json.get('business').get('dissolutionDate')
    assert rv.json.get('business').get('identifier') == identifier


def test_get_business_info_missing_business(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    factory_business_model(legal_name='legal_name',
                           identifier='CP7654321',
                           founding_date=datetime.utcfromtimestamp(0),
                           last_ledger_timestamp=datetime.utcfromtimestamp(0),
                           last_modified=datetime.utcfromtimestamp(0),
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None)
    identifier = 'CP0000001'
    rv = client.get(f'/api/v2/businesses/{identifier}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_get_business_with_allowed_filings(session, client, jwt):
    """Assert that the allowed filings are returned with business."""
    identifier = 'CP0000001'
    factory_business(identifier, state=Business.State.HISTORICAL)

    rv = client.get(f'/api/v2/businesses/{identifier}?allowed_filings=true',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['business']['allowedFilings']



@pytest.mark.parametrize('test_name, legal_type, identifier, has_missing_business_info, compliance_warning_expected', [
    ('WARNINGS_EXIST_MISSING_DATA', 'SP', 'FM0000001', True, True),
    ('WARNINGS_EXIST_MISSING_DATA', 'GP', 'FM0000002', True, True),
    ('NO_WARNINGS_EXIST_NO_MISSING_DATA', 'SP', 'FM0000003', False, False),
    ('NO_WARNINGS_EXIST_NO_MISSING_DATA', 'GP', 'FM0000004', False, False),
    ('NO_WARNINGS_NON_FIRM', 'CP', 'CP7654321', True, False),
    ('NO_WARNINGS_NON_FIRM', 'BEN', 'CP7654321', True, False),
    ('NO_WARNINGS_NON_FIRM', 'BC', 'BC7654321', True, False),
])
def test_get_business_with_incomplete_info(session, client, jwt, test_name, legal_type, identifier, has_missing_business_info,
                                           compliance_warning_expected):
    """Assert that SP/GPs with missing business info, populating complianceWarnings list."""

    if has_missing_business_info:
        factory_business(entity_type=legal_type, identifier=identifier)
    else:
        create_business(legal_type=legal_type,
                        identifier=identifier,
                        create_office=True,
                        create_office_mailing_address=True,
                        create_office_delivery_address=True,
                        firm_num_persons_roles=2,
                        create_firm_party_address=True,
                        filing_types=['registration'],
                        filing_has_completing_party=[True],
                        create_completing_party_address=[True])

    session.commit()
    rv = client.get(f'/api/v2/businesses/{identifier}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    rv_json = rv.json

    if compliance_warning_expected:
        assert len(rv_json['business']['complianceWarnings']) > 0
    else:
        assert len(rv_json['business']['complianceWarnings']) == 0
