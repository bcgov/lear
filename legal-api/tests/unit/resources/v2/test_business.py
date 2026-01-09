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
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CORRECTION_AR,
    COURT_ORDER_FILING_TEMPLATE,
    FILING_HEADER,
    FILING_TEMPLATE,
    INCORPORATION
)

from legal_api.models import Amalgamation, Business, Filing, RegistrationBootstrap
from legal_api.services.authz import ACCOUNT_IDENTITY, PUBLIC_USER, STAFF_ROLE, SYSTEM_ROLE
from legal_api.services import flags
from legal_api.utils.datetime import datetime
from tests import integration_affiliation
from tests.unit.models import factory_business, factory_pending_filing
from tests.unit.services.warnings import create_business
from tests.unit.services.utils import create_header
from tests.unit.models import factory_completed_filing

from unittest.mock import MagicMock

def factory_business_model(legal_name,
                           identifier,
                           founding_date,
                           last_ledger_timestamp,
                           last_modified,
                           fiscal_year_end_date=None,
                           tax_id=None,
                           dissolution_date=None,
                           legal_type=None,
                           no_dissolution=False):
    """Return a valid Business object stamped with the supplied designation."""
    from legal_api.models import Business as BusinessModel
    b = BusinessModel(legal_name=legal_name,
                      identifier=identifier,
                      founding_date=founding_date,
                      last_ledger_timestamp=last_ledger_timestamp,
                      last_modified=last_modified,
                      fiscal_year_end_date=fiscal_year_end_date,
                      dissolution_date=dissolution_date,
                      tax_id=tax_id,
                      no_dissolution=no_dissolution
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
    'registration',
    'amalgamationApplication',
    'continuationIn',
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


@pytest.mark.parametrize('test_name,role,calls_auth', [
    ('public-user', PUBLIC_USER, True),
    ('account-identity', ACCOUNT_IDENTITY, False),
    ('staff', STAFF_ROLE, False),
    ('system', SYSTEM_ROLE, False)
])
def test_get_business_info(app, session, client, jwt, requests_mock, test_name, role, calls_auth):
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

    if calls_auth:
        # should not call auth for staff/system/account_identity
        requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': ['view']})

    rv = client.get('/api/v2/businesses/' + identifier,
                    headers=create_header(jwt, [role], identifier))

    print('business json', rv.json)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['business']['identifier'] == identifier
    assert rv.json['business']['hasCorrections'] == False

    print('valid schema?', registry_schemas.validate(rv.json, 'business'))

    assert registry_schemas.validate(rv.json, 'business')


@pytest.mark.parametrize('test_name,role,amalgamated', [
    ('regular', PUBLIC_USER, False),
    ('amalgamated', PUBLIC_USER, True),
])
def test_get_business_slim_info(app, session, client, jwt, requests_mock, test_name, role, amalgamated):
    """Assert that the business slim info can be received with the expected data."""
    identifier = 'BC7654321'
    legal_type = 'BC'
    legal_name = identifier + ' legal name'
    tax_id = '123'
    business = factory_business_model(legal_name=legal_name,
                                      legal_type=legal_type,
                                      identifier=identifier,
                                      founding_date=datetime.fromtimestamp(0),
                                      last_ledger_timestamp=datetime.fromtimestamp(0),
                                      last_modified=datetime.fromtimestamp(0),
                                      fiscal_year_end_date=None,
                                      tax_id=tax_id,
                                      dissolution_date=None)

    if amalgamated:
        filing = copy.deepcopy(FILING_TEMPLATE)
        filing['filing'].pop('business')
        filing['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
        filing['filing']['header']['name'] = 'amalgamationApplication'
        filing = factory_completed_filing(business, filing)
        business.state_filing_id = filing.id
        business.state = 'HISTORICAL'
        amalgamation = Amalgamation(
            amalgamation_type=Amalgamation.AmalgamationTypes.regular,
            business_id=business.id,
            filing_id=filing.id,
            amalgamation_date=datetime.utcnow(),
            court_approval=True
        )
        amalgamation.save()
        business.save()

    # with patch('legal_api.services.warnings.business.business_checks.business.involuntary_dissolution_check', return_value=filing.id):
    rv = client.get(f'/api/v2/businesses/{identifier}?slim=true' ,
                    headers=create_header(jwt, [role], identifier))

    print('business json', rv.json)

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['business']['identifier'] == identifier
    assert rv.json['business']['legalType'] == legal_type
    assert rv.json['business']['taxId'] == tax_id
    assert rv.json['business'].get('state') is not None
    assert rv.json['business'].get('goodStanding') is not None
    if amalgamated:
        assert rv.json['business'].get('amalgamatedInto') is not None


@pytest.mark.parametrize('test_name, slim_version, auth_check_on', [
    ('slim business request', True, True),
    ('regular business request', False, True),
    ('regular business request with the auth-check flag turned off', False, False)
])
def test_get_business_with_unauthoized_role(app, session, client, jwt, monkeypatch, requests_mock, test_name, slim_version, auth_check_on):
    """
    Assert that the public users with no 'view' role cannot access the full business info.
    But they can access the slim data.
    """
    # original function that check if a feature flag is on
    is_feature_flag_on = flags.is_on

    # mocked feature flag check function:
    # when the flag is 'enable-auth-v2-business', whether it is on is controlled by 'auth_check_on'
    def check_feature_flag(flag_name):
        if flag_name == 'enable-auth-v2-business':
            return auth_check_on
        else:
            return is_feature_flag_on(flag_name)
    monkeypatch.setattr(flags, "is_on", check_feature_flag)

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

    headers = create_header(jwt, [PUBLIC_USER], identifier)
    requests_mock.get(f"{app.config.get('AUTH_SVC_URL')}/entities/{identifier}/authorizations", json={'roles': []})

    if slim_version:
        rv = client.get('/api/v2/businesses/' + identifier + '?slim=true', headers=headers)
        assert rv.status_code == HTTPStatus.OK
    else:
        rv = client.get('/api/v2/businesses/' + identifier, headers=headers)
        assert flags.is_on('enable-auth-v2-business') == auth_check_on
        assert rv.status_code == (HTTPStatus.UNAUTHORIZED if auth_check_on else HTTPStatus.OK)


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
    business.no_dissolution = True
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


@pytest.mark.parametrize('identifier, legal_type, nr_number, legal_name, result', [
    ('Tb31yQIuBw', Business.LegalTypes.COMP.value, None, None, 'Numbered Limited Company'),
    ('Tb31yQIuBw', Business.LegalTypes.COMP.value, 'NR 1245670', 'Test NR name', 'Test NR name'),
    ('Tb31yQIuBw', Business.LegalTypes.COMP.value, None, '0870754 B.C. LTD.', '0870754 B.C. LTD.')
    # Add more scenarios here as needed
])
def test_draft_amalgamation_name_selection(session, client, jwt, identifier, legal_type, nr_number, legal_name, result):
    """Test draft regular amalgamation with various name selection scenarios."""

    # Setup a temporary registration and draft filing
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()

    json_data = {
        'filing': {
            'header': {
                'name': 'amalgamationApplication',
                'date': '2019-04-08',
                'certifiedBy': 'full name'
            }
        }
    }
    json_data['filing']['amalgamationApplication'] = {
        'type': 'regular',
        'nameRequest': {
            'nrNumber': nr_number,
            'legalName': legal_name,
            'legalType': legal_type
        }
    }

    # Save the draft filing
    filing = factory_pending_filing(None, json_data)
    filing.temp_reg = identifier
    filing.save()

    # Make a request to retrieve the draft businesses
    rv = client.post('/api/v2/businesses/search', json={'identifiers': [identifier]}, headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK, "Failed to retrieve draft businesses"

    # Extract and assert on the draft entity
    draft_entities = rv.json.get('draftEntities', [])
    assert len(draft_entities) == 1, "Did not find expected draft entity"

    draft_entity = draft_entities[0]
    assert draft_entity.get('legalName') == result, f"Expected legal name to be Amalgamated Business but got '{draft_entity.get('legalName')}'"


def test_post_affiliated_businesses(session, client, jwt):
    """Assert that the affiliated businesses endpoint returns as expected."""
    # setup
    identifiers = ['CP1234567', 'BC1234567', 'Tb31yQIuBv', 'Tb31yQIuBw', 'Tb31yQIuBx', 'Tb31yQIuBy', 'Tb31yQIuBz']
    businesses = [
        (identifiers[0], Business.LegalTypes.COOP.value, None),
        (identifiers[1], Business.LegalTypes.BCOMP.value, '123456789BC0001')]
    draft_businesses = [
        (identifiers[2], 'incorporationApplication', Business.LegalTypes.COOP.value, None),
        (identifiers[3], 'incorporationApplication', Business.LegalTypes.BCOMP.value, None),
        (identifiers[4], 'continuationIn', Business.LegalTypes.BCOMP_CONTINUE_IN.value, None),
        (identifiers[5], 'amalgamationApplication', Business.LegalTypes.COMP.value, 'NR 1234567'),
        (identifiers[6], 'registration', Business.LegalTypes.SOLE_PROP.value, 'NR 1234567'),
    ]

    # NB: these are real businesses now so temp should not get returned
    old_draft_businesses = [identifiers[2]]

    for business in businesses:
        factory_business_model(legal_name=business[0] + 'name',
                               identifier=business[0] if business[0][0] != 'T' else 'BC7654321',
                               founding_date=datetime.utcfromtimestamp(0),
                               last_ledger_timestamp=datetime.utcfromtimestamp(0),
                               last_modified=datetime.utcfromtimestamp(0),
                               fiscal_year_end_date=None,
                               tax_id=business[2],
                               dissolution_date=None,
                               legal_type=business[1])

    for draft_business in draft_businesses:
        filing_name = draft_business[1]
        temp_reg = RegistrationBootstrap()
        temp_reg._identifier = draft_business[0]
        temp_reg.save()
        json_data = copy.deepcopy(FILING_HEADER)
        json_data['filing']['header']['name'] = filing_name
        json_data['filing']['header']['identifier'] = draft_business[0]
        del json_data['filing']['business']
        json_data['filing'][filing_name] = {
            'nameRequest': {
                'legalType': draft_business[2]
            }
        }
        if draft_business[3]:
            json_data['filing'][filing_name]['nameRequest'] = {
                **json_data['filing'][filing_name]['nameRequest'],
                'nrNumber': draft_business[3],
                'legalName': 'name example',
            }
        if filing_name == 'amalgamationApplication':
            json_data['filing'][filing_name] = {
                **json_data['filing'][filing_name],
                'type': 'regular'
            }
        filing = factory_pending_filing(None, json_data)
        filing.temp_reg = draft_business[0]
        if draft_business[0] in old_draft_businesses:
            # adding a business id informs the search that it is associated with a completed business
            business = Business.find_by_identifier(identifiers[0])
            filing.business_id = business.id
        filing.save()

    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': identifiers},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json['businessEntities']) == len(businesses)
    assert len(rv.json['draftEntities']) == len(draft_businesses) - len(old_draft_businesses)

    # verify 'legalName' for each draft entity
    for draft_entity in rv.json['draftEntities']:
        identifier = draft_entity['identifier']
        expected_draft_business = next((draftb for draftb in draft_businesses if draftb[0] == identifier), None)
        assert draft_entity['legalType'] == expected_draft_business[2]
        assert draft_entity['draftType'] == Filing.FILINGS.get(expected_draft_business[1], {}).get('temporaryCorpTypeCode')
        assert draft_entity['draftStatus'] == Filing.Status.PENDING.value
        assert 'effectiveDate' not in draft_entity
        if expected_draft_business and expected_draft_business[3]:
            # if NR number is present, assert 'legalName' is also expected to be present
            assert 'legalName' in draft_entity
        else:
            # assert 'legalName' is numberedDescription if no NR number is provided
            assert (draft_entity.get('legalName') ==
                    Business.BUSINESSES[expected_draft_business[2]]['numberedDescription'])


@pytest.mark.parametrize('is_future_effective', [
    False,
    True
])
def test_filing_is_future_effective(session, client, jwt, is_future_effective):
    """Test draft regular amalgamation with various name selection scenarios."""
    # Setup a temporary registration and draft filing
    filing_name = 'incorporationApplication'
    identifier = 'Tb31yQIuBw'
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = identifier
    temp_reg.save()

    json_data = copy.deepcopy(FILING_HEADER)
    json_data['filing']['header']['name'] = filing_name
    json_data['filing']['header']['identifier'] = identifier
    del json_data['filing']['business']
    json_data['filing'][filing_name] = {
        'nameRequest': {
            'legalType': 'BEN'
        }
    }

    # Save the draft filing
    filing = factory_pending_filing(None, json_data)
    filing.temp_reg = identifier
    filing.payment_completion_date = datetime.utcnow()
    filing.effective_date = datetime.utcnow()
    if is_future_effective:
        filing.effective_date = datetime.add_business_days(filing.effective_date, 1)
    filing.save()

    # Make a request to retrieve the draft businesses
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': [identifier]},
                     headers=create_header(jwt, [SYSTEM_ROLE]))

    assert rv.status_code == HTTPStatus.OK

    # Extract and assert on the draft entity
    draft_entities = rv.json.get('draftEntities', [])
    assert len(draft_entities) == 1

    draft_entity = draft_entities[0]
    if is_future_effective:
        assert draft_entity.get('effectiveDate') == filing.effective_date.isoformat()
    else:
        assert 'effectiveDate' not in draft_entity


def test_post_affiliated_businesses_unathorized(session, client, jwt):
    """Assert that the affiliated businesses endpoint unauthorized if not a system token."""
    rv = client.post('/api/v2/businesses/search',
                     json={'identifiers': ['CP1234567']},
                     headers=create_header(jwt, [STAFF_ROLE]))
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_affiliated_businesses_invalid(session, client, jwt):
    """Assert that the affiliated businesses endpoint bad request when identifiers not given."""
    rv = client.post('/api/v2/businesses/search',
                     json={},
                     headers=create_header(jwt, [SYSTEM_ROLE]))
    assert rv.status_code == HTTPStatus.BAD_REQUEST


def test_get_could_file(session, client, jwt, monkeypatch):
    """Assert that the cold file is returned."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag, _user, _account_id: "changeOfLiquidators.appointLiquidator,changeOfLiquidators.ceaseLiquidator,changeOfLiquidators.changeAddressLiquidator,changeOfLiquidators.intentToLiquidate,changeOfLiquidators.liquidationReport,changeOfReceivers.amendReceiver,changeOfReceivers.appointReceiver,changeOfReceivers.ceaseReceiver,changeOfReceivers.changeAddressReceiver,dissolution.delay,transition"
        if flag == 'enabled-specific-filings' else {}
    )
    monkeypatch.setattr(
        'legal_api.models.User.get_or_create_user_by_jwt',
        lambda _: None
    )
    identifier = 'BC0000001'
    rv = client.get('/api/v2/businesses/allowable/BC/ACTIVE',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    expected = [
        {
            "displayName": "Admin Freeze",
            "name": "adminFreeze"
        },
        {
            "displayName": "Request for AGM Extension",
            "name": "agmExtension"
        },
        {
            "displayName": "AGM Location Change",
            "name": "agmLocationChange"
        },
        {
            "displayName": "Alteration",
            "name": "alteration"
        },
        {
            "displayName": "Amalgamation Application (Regular)",
            "name": "amalgamationApplication",
            "type": "regular"
        },
        {
            "displayName": "Amalgamation Application Short-form (Vertical)",
            "name": "amalgamationApplication",
            "type": "vertical"
        },
        {
            "displayName": "Amalgamation Application Short-form (Horizontal)",
            "name": "amalgamationApplication",
            "type": "horizontal"
        },
        {
            "displayName": "Amalgamation Out",
            "name": "amalgamationOut"
        },
        {
            "displayName": "Annual Report",
            "name": "annualReport"
        },
        {
            "displayName": "Address Change",
            "name": "changeOfAddress"
        },
        {
            "displayName": "Director Change",
            "name": "changeOfDirectors"
        },
        {
            "displayName": "Notice of Appointment of Liquidator",
            "name": "changeOfLiquidators",
            "type": "appointLiquidator"
        },
        {
            "displayName": "Notice of Ceasing to Act as Liquidator",
            "name": "changeOfLiquidators",
            "type": "ceaseLiquidator"
        },
        {
            "displayName": "Notice of Change of Address of Liquidator and/or Liquidation Records Office",
            "name": "changeOfLiquidators",
            "type": "changeAddressLiquidator"
        },
        {
            "displayName": "Statement of Intent to Liquidate",
            "name": "changeOfLiquidators",
            "type": "intentToLiquidate"
        },
        {
            "displayName": "Liquidation Report",
            "name": "changeOfLiquidators",
            "type": "liquidationReport"
        },
        {
            "displayName": "Officer Change",
            "name": "changeOfOfficers"
        },
        {
            "displayName": "Amend Receiver Information",
            "name": "changeOfReceivers",
            "type": "amendReceiver"
        },
        {
            "displayName": "Notice of Appointment of Receiver or Receiver Manager",
            "name": "changeOfReceivers",
            "type": "appointReceiver"
        },
        {
            "displayName": "Notice of Ceasing to Act as Receiver or Receiver Manager",
            "name": "changeOfReceivers",
            "type": "ceaseReceiver"
        },
        {
            "displayName": "Notice of Receiver Change of Address Filing",
            "name": "changeOfReceivers",
            "type": "changeAddressReceiver"
        },
        {
            "displayName": "6-Month Consent to Amalgamate Out",
            "name": "consentAmalgamationOut"
        },
        {
            "displayName": "6-Month Consent to Continue Out",
            "name": "consentContinuationOut"
        },
        {
            "displayName": "Continuation Out",
            "name": "continuationOut"
        },
        {
            "displayName": "Register Correction Application",
            "name": "correction"
        },
        {
            "displayName": "Court Order",
            "name": "courtOrder"
        },
        {
            "displayName": "Voluntary Dissolution",
            "name": "dissolution",
            "type": "voluntary"
        },
        {
            "displayName": "Administrative Dissolution",
            "name": "dissolution",
            "type": "administrative"
        },
        {
            "displayName": "Delay of Dissolution",
            "name": "dissolution",
            "type": "delay"
        },
        {
            "displayName": "BC Limited Company Incorporation Application",
            "name": "incorporationApplication"
        },
        {
            "displayName": "Correction - Put Back Off",
            "name": "putBackOff",
        },
        {
            "displayName": "Registrar's Notation",
            "name": "registrarsNotation"
        },
        {
            "displayName": "Registrar's Order",
            "name": "registrarsOrder"
        },
        {
            "displayName": "Transition Application",
            "name": "transition"
        },
        {
            "displayName": "Limited Restoration Extension Application",
            "name": "restoration",
            "type": "limitedRestorationExtension"
        },
        {
            "displayName": "Conversion to Full Restoration Application",
            "name": "restoration",
            "type": "limitedRestorationToFull"
        },
        {
            "displayName": "Notice of Withdrawal",
            "name": "noticeOfWithdrawal"
        }
    ]

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['couldFile']
    assert rv.json['couldFile']['filing']
    assert rv.json['couldFile']['filing']['filingTypes']
    assert len(rv.json['couldFile']['filing']['filingTypes']) > 0
    assert rv.json['couldFile']['filing']['filingTypes'] == expected
