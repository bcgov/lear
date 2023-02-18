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
from registry_schemas.example_data import ANNUAL_REPORT, CORRECTION_AR, COURT_ORDER_FILING_TEMPLATE, FILING_HEADER,\
    FILING_TEMPLATE, INCORPORATION

from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.services.authz import STAFF_ROLE, SYSTEM_ROLE
from legal_api.utils.datetime import datetime
from tests import integration_affiliation
from tests.unit.models import factory_business, factory_pending_filing
from tests.unit.services.warnings import create_business
from tests.unit.services.utils import create_header
from tests.unit.models import factory_completed_filing


def factory_business_model(legal_name,
                           identifier,
                           founding_date,
                           last_ledger_timestamp,
                           last_modified,
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None,
                           legal_type=None):
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
    if legal_type:
        b.legal_type = legal_type
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
    assert rv.json['business']['hasCorrections'] == False

    print('valid schema?', registry_schemas.validate(rv.json, 'business'))

    assert registry_schemas.validate(rv.json, 'business')


def test_get_business_with_correction_filings(session, client, jwt):
    """Assert that the business info sets hasCorrections property."""
    identifier = 'CP7654321'
    legal_name = identifier + ' legal name'
    business = factory_business_model(legal_name=legal_name,
                                      identifier=identifier,
                                      founding_date=datetime.utcfromtimestamp(0),
                                      last_ledger_timestamp=datetime.utcfromtimestamp(0),
                                      last_modified=datetime.utcfromtimestamp(0),
                                      fiscal_year_end_date=None,
                                      tax_id=None,
                                      dissolution_date=None)

    corrected_filing = factory_completed_filing(business, ANNUAL_REPORT)

    f = copy.deepcopy(CORRECTION_AR)
    f['filing']['header']['identifier'] = business.identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id
    factory_completed_filing(business, f)

    rv = client.get('/api/v2/businesses/' + business.identifier,
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.json['business']['identifier'] == identifier
    assert rv.json['business']['hasCorrections'] == True


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


@pytest.mark.parametrize('test_name, legal_type, identifier, has_missing_business_info, missing_business_info_warning_expected', [
    ('WARNINGS_EXIST_MISSING_DATA', 'SP', 'FM0000001', True, True),
    ('WARNINGS_EXIST_MISSING_DATA', 'GP', 'FM0000002', True, True),
    ('NO_WARNINGS_EXIST_NO_MISSING_DATA', 'SP', 'FM0000003', False, False),
    ('NO_WARNINGS_EXIST_NO_MISSING_DATA', 'GP', 'FM0000004', False, False),
    ('NO_WARNINGS_NON_FIRM', 'CP', 'CP7654321', True, False),
    ('NO_WARNINGS_NON_FIRM', 'BEN', 'CP7654321', True, False),
    ('NO_WARNINGS_NON_FIRM', 'BC', 'BC7654321', True, False),
])
def test_get_business_with_incomplete_info(session, client, jwt, test_name, legal_type, identifier, has_missing_business_info,
                                           missing_business_info_warning_expected):
    """Assert that SP/GPs with missing business info is populating warnings list."""

    if has_missing_business_info:
        business = factory_business(entity_type=legal_type, identifier=identifier)
    else:
        business = create_business(legal_type=legal_type,
                                   identifier=identifier,
                                   create_office=True,
                                   create_office_mailing_address=True,
                                   create_office_delivery_address=True,
                                   firm_num_persons_roles=2,
                                   create_firm_party_address=True,
                                   filing_types=['registration'],
                                   filing_has_completing_party=[True],
                                   create_completing_party_address=[True]
                                   )
    business.start_date = datetime.utcnow().date()
    business.save()
    session.commit()
    rv = client.get(f'/api/v2/businesses/{identifier}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    rv_json = rv.json

    if missing_business_info_warning_expected:
        # TODO remove complianceWarnings check when UI has been integrated to use warnings instead of complianceWarnings
        assert len(rv_json['business']['complianceWarnings']) > 0
        assert len(rv_json['business']['warnings']) > 0
        for warning in rv_json['business']['warnings']:
            assert warning['warningType'] == 'MISSING_REQUIRED_BUSINESS_INFO'
    else:
        # TODO remove complianceWarnings check when UI has been integrated to use warnings instead of complianceWarnings
        assert len(rv_json['business']['complianceWarnings']) == 0
        assert len(rv_json['business']['warnings']) == 0


def test_get_business_with_court_orders(session, client, jwt):
    """Assert that the business info sets hasCourtOrders property."""
    identifier = 'CP7654321'
    legal_name = identifier + ' legal name'
    business = factory_business_model(legal_name=legal_name,
                                      identifier=identifier,
                                      founding_date=datetime.utcfromtimestamp(0),
                                      last_ledger_timestamp=datetime.utcfromtimestamp(0),
                                      last_modified=datetime.utcfromtimestamp(0),
                                      fiscal_year_end_date=None,
                                      tax_id=None,
                                      dissolution_date=None)

    factory_completed_filing(business, COURT_ORDER_FILING_TEMPLATE)

    rv = client.get('/api/v2/businesses/' + business.identifier,
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.json['business']['identifier'] == identifier
    assert rv.json['business']['hasCourtOrders'] == True


def test_post_affiliated_businesses(session, client, jwt):
    """Assert that the affiliated businesses endpoint returns as expected."""
    # setup
    identifiers = ['CP1234567', 'BC1234567', 'Tb31yQIuBw', 'Tb31yQIuBq']
    businesses = [
        (identifiers[0], Business.LegalTypes.COOP.value, None),
        (identifiers[1], Business.LegalTypes.BCOMP.value, '123456789BC0001')]
    draft_businesses = [
        (identifiers[2], Business.LegalTypes.BCOMP.value, None),
        (identifiers[3], Business.LegalTypes.SOLE_PROP.value, 'NR 1234567')]

    for business in businesses:
        factory_business_model(legal_name=business[0] + 'name',
                               identifier=business[0],
                               founding_date=datetime.utcfromtimestamp(0),
                               last_ledger_timestamp=datetime.utcfromtimestamp(0),
                               last_modified=datetime.utcfromtimestamp(0),
                               fiscal_year_end_date=None,
                               tax_id=business[2],
                               dissolution_date=None,
                               legal_type=business[1])

    for draft_business in draft_businesses:
        filing_name = 'incorporationApplication' if draft_business[1] == Business.LegalTypes.BCOMP.value else 'registration'
        temp_reg = RegistrationBootstrap()
        temp_reg._identifier = draft_business[0]
        temp_reg.save()
        json_data = copy.deepcopy(FILING_HEADER)
        json_data['filing']['header']['name'] = filing_name
        json_data['filing']['header']['identifier'] = draft_business[0]
        json_data['filing']['header']['legalType'] = draft_business[1]
        if draft_business[2]:
            json_data['filing'][filing_name] = {
                'nameRequest': {'nrNumber': draft_business[2]}
            }
        filings = factory_pending_filing(None, json_data)
        filings.temp_reg = draft_business[0]
        filings.save()

    rv = client.post('/api/v2/businesses/affiliations',
                     json={'identifiers': identifiers},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessAffiliations']) == len(businesses)
    assert len(rv.json['draftAffiliations']) == len(draft_businesses)


def test_post_affiliated_businesses_unathorized(session, client, jwt):
    """Assert that the affiliated businesses endpoint unauthorized if not a system token."""
    rv = client.post('/api/v2/businesses/affiliations',
                     json={'identifiers': ['CP1234567']},
                     headers=create_header(jwt, [STAFF_ROLE]))
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_affiliated_businesses_invalid(session, client, jwt):
    """Assert that the affiliated businesses endpoint bad request when identifiers not given."""
    rv = client.post('/api/v2/businesses/affiliations',
                     json={},
                     headers=create_header(jwt, [SYSTEM_ROLE]))
    assert rv.status_code == HTTPStatus.BAD_REQUEST
