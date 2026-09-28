# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the colin sync end-point."""
import copy
from http import HTTPStatus

from sqlalchemy import text

from business_model.models import Business, Filing, PartyRole
from business_model.models.colin_event_id import ColinEventId
from business_model.models.db import VersioningProxy
from legal_api.services.authz import COLIN_SVC_ROLE
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CORRECTION_AR,
    CORRECTION_COL,
    CORRECTION_COR,
    FILING_HEADER
)
from tests.unit.services.utils import create_header
from tests.unit.models import (
    factory_address,
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_error_filing,
    factory_party_role,
    factory_filing,
    factory_pending_filing
)
from tests.unit.models import db


def test_get_internal_filings(session, client, jwt):
    """Assert that the internal filings get endpoint returns all completed filings without colin ids."""
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)

    filing1 = factory_completed_filing(b, ANNUAL_REPORT)
    filing2 = factory_completed_filing(b, ANNUAL_REPORT)
    filing3 = factory_pending_filing(b, ANNUAL_REPORT)
    filing4 = factory_filing(b, ANNUAL_REPORT)
    filing5 = factory_error_filing(b, ANNUAL_REPORT)
    filing6 = factory_completed_filing(b, CORRECTION_AR)

    assert filing1.status == Filing.Status.COMPLETED.value
    # completed with colin_event_id
    print(filing2.colin_event_ids)
    assert len(filing2.colin_event_ids) == 0
    colin_event_id = ColinEventId()
    colin_event_id.colin_event_id = 12345
    filing2.colin_event_ids.append(colin_event_id)
    filing2.save()
    assert filing2.status == Filing.Status.COMPLETED.value
    assert filing2.colin_event_ids
    # pending with no colin_event_ids
    assert filing3.status == Filing.Status.PENDING.value
    # draft with no colin_event_ids
    assert filing4.status == Filing.Status.DRAFT.value
    # error with no colin_event_ids
    assert filing5.status == Filing.Status.PAID.value
    # completed correction with no colin_event_ids (returned so colin-api's 501 blocks the coop's sync)
    assert filing6.status == Filing.Status.COMPLETED.value

    # test endpoint returned the completed filings with no colin id set
    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filings = rv.json.get('filings')
    assert len(filings) == 2
    assert filings[0]['filingId'] == filing1.id
    assert filings[1]['filingId'] == filing6.id


def test_get_internal_filings_backfills_business_fields(session, client, jwt):
    """Assert legalType and legalName are backfilled when the filing json predates them."""
    identifier = 'CP7654322'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing_json = copy.deepcopy(ANNUAL_REPORT)
    filing_json['filing']['business']['identifier'] = identifier
    del filing_json['filing']['business']['legalType']
    del filing_json['filing']['business']['legalName']
    filing = factory_completed_filing(b, filing_json)

    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filing_json = next(f for f in rv.json.get('filings') if f['filingId'] == filing.id)
    assert filing_json['filing']['business']['legalType'] == b.legal_type
    assert filing_json['filing']['business']['legalName'] == b.legal_name


def test_get_internal_filings_marks_no_op_correction_lear_only(session, client, jwt):
    """Assert a correction with no colin relevant changes is marked lear_only and not returned."""
    identifier = 'BC7654321'
    b = factory_business(identifier, entity_type=Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)
    filing = factory_completed_filing(b, CORRECTION_AR)
    filing._meta_data = {}
    filing.save()
    assert not filing.lear_only

    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    assert all(f['filingId'] != filing.id for f in rv.json.get('filings'))
    filing = Filing.find_by_id(filing.id)
    assert filing.lear_only


def test_patch_internal_filings(session, client, jwt):
    """Assert that the internal filings patch endpoint updates the colin_event_id."""
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing = factory_completed_filing(b, ANNUAL_REPORT)
    colin_id = 1234

    # make request
    rv = client.patch(f'/api/v2/businesses/internal/filings/{filing.id}',
                      json={'colinIds': [colin_id]},
                      headers=create_header(jwt, [COLIN_SVC_ROLE])
                      )

    # test result
    assert rv.status_code == HTTPStatus.ACCEPTED
    filing = Filing.find_by_id(filing.id)
    assert colin_id in ColinEventId.get_by_filing_id(filing.id)
    assert rv.json['filing']['header']['filingId'] == filing.id
    assert colin_id in rv.json['filing']['header']['colinIds']


def test_get_colin_id(session, client, jwt):
    """Assert the internal/filings/colin_id get endpoint returns properly."""
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing = factory_completed_filing(b, ANNUAL_REPORT)
    colin_event_id = ColinEventId()
    colin_event_id.colin_event_id = 1234
    filing.colin_event_ids.append(colin_event_id)
    filing.save()

    rv = client.get(f'/api/v2/businesses/internal/filings/colin_id/{colin_event_id.colin_event_id}',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    assert rv.json == {'colinId': colin_event_id.colin_event_id}

    rv = client.get(f'/api/v2/businesses/internal/filings/colin_id/{1}',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.NOT_FOUND


def test_get_colin_last_update(session, client, jwt):
    """Assert the get endpoint for ColinLastUpdate returns last updated colin id."""
    # setup
    colin_id = 1234
    db.session.execute(text(
        f"""
        insert into colin_last_update (last_update, last_event_id)
        values (current_timestamp, {colin_id})
        """
    ))

    rv = client.get('/api/v2/businesses/internal/filings/colin_id',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    assert rv.json == {'maxId': colin_id}


def test_post_colin_last_update(session, client, jwt):
    """Assert the internal/filings/colin_id post endpoint updates the colin_last_update table."""
    colin_id = 1234
    rv = client.post(f'/api/v2/businesses/internal/filings/colin_id/{colin_id}',
                     headers=create_header(jwt, [COLIN_SVC_ROLE])
                     )
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json == {'maxId': colin_id}


def test_get_completed_filings_for_colin_corps_correction(session, client, jwt):
    """Assert that corps corrections are returned as expected."""
    # setup
    identifier = 'BC7654321'
    b = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    correction_cod = copy.deepcopy(CORRECTION_COL)
    correction_cod['filing']['correction']['correctedFilingType'] = 'changeOfDirectors'
    correction_cod['filing']['correction']['relationships'][0]['roles'][0]['roleType'] = 'Director'

    filing_col = factory_completed_filing(b, CORRECTION_COL)
    # Filer will set this for corrections on liquidators only
    filing_col.lear_only = True
    filing_col.save()
    filing_cor = factory_completed_filing(b, CORRECTION_COR)
    # Filer will set this for corrections on receivers only
    filing_cor.lear_only = True
    filing_cor.save()
    filing_cod = factory_completed_filing(b, correction_cod)
    # Need to apply the relationships to the db
    for filing in [filing_col, filing_cor, filing_cod]:
        for relationship in filing.filing_json['filing']['correction']['relationships']:
            mailing_address = factory_address(relationship['mailingAddress']['streetAddress'], 'mailing')
            delivery_address = factory_address(relationship['deliveryAddress']['streetAddress'], 'delivery')
            officer = {
                'firstName': relationship['entity']['givenName'],
                'lastName': relationship['entity']['familyName'],
                'middleInitial': relationship['entity'].get('middleInitial'),
                'partyType': 'person',
                'organizationName': ''
            }
            role_type = PartyRole.RoleTypes.DIRECTOR
            if relationship['roles'][0]['roleType'].lower() == 'receiver':
                role_type = PartyRole.RoleTypes.RECEIVER
            elif relationship['roles'][0]['roleType'].lower() == 'liquidator':
                role_type = PartyRole.RoleTypes.LIQUIDATOR

            party_role = factory_party_role(
                delivery_address,
                mailing_address,
                officer,
                filing.effective_date,
                None,
                role_type
            )
            b.party_roles.append(party_role)
            b.save()
        # need to set the filing transaction id to match the transaction id of the last 'save'
        # - symptom of having separate transactions per 'save' during the test setup
        # - in reality these are set to the same id during the filer processing
        filing.transaction_id = VersioningProxy.get_transaction_id(db.session()) - 1
        filing.save()

    assert filing_col.status == Filing.Status.COMPLETED.value
    assert filing_cor.status == Filing.Status.COMPLETED.value
    assert filing_cod.status == Filing.Status.COMPLETED.value

    # test endpoint returned filing1 only (completed, no corrections, with no colin id set)
    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filings = rv.json.get('filings')
    # Should only return the filing with directors
    assert len(filings) == 1
    # Should have been mapped to expected filing json
    assert filings[0]['filingId'] == filing_cod.id
    assert filings[0]['filing']['correction']['correctedFilingType'] == 'changeOfDirectors'
    assert filings[0]['filing']['correction']['correctedFilingType'] == 'changeOfDirectors'
    assert filings[0]['filing']['correction']['partyChanged'] == True
    parties = filings[0]['filing']['correction']['parties']
    assert len(parties) == 1
    director = parties[0]
    assert director['officer']['firstName'] == correction_cod['filing']['correction']['relationships'][0]['entity']['givenName']
    assert director['mailingAddress']['streetAddress'] == correction_cod['filing']['correction']['relationships'][0]['mailingAddress']['streetAddress']
    assert director['deliveryAddress']['streetAddress'] == correction_cod['filing']['correction']['relationships'][0]['deliveryAddress']['streetAddress']
    assert len(director['roles']) == 1
    assert director['roles'][0]['roleType'] == 'Director'
    assert director['roles'][0]['appointmentDate']

def test_get_completed_filings_for_colin_short_form_amalgamation(session, client, jwt):
    """Assert a short-form amalgamation sync payload is the stored filing json, passed through unchanged."""
    identifier = 'BC7654322'
    b = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'amalgamationApplication'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = 'BC'
    filing_json['filing']['amalgamationApplication'] = copy.deepcopy(AMALGAMATION_APPLICATION)
    aml = filing_json['filing']['amalgamationApplication']
    aml['type'] = 'vertical'
    aml['nameRequest']['legalName'] = 'Holding Business Ltd.'
    aml['amalgamatingBusinesses'] = [
        {'role': 'holding', 'identifier': 'BC5556667'},
        {'role': 'amalgamating', 'identifier': 'BC5556668'}
    ]
    aml['shareStructure']['resolutionDates'] = ['2020-05-13']

    filing = factory_completed_filing(b, filing_json)
    assert filing.status == Filing.Status.COMPLETED.value

    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filings = rv.json.get('filings')
    assert len(filings) == 1
    synced = filings[0]['filing']
    # the header is never poisoned and the certified sections flow through untouched
    assert synced['header']['name'] == 'amalgamationApplication'
    assert synced['amalgamationApplication']['nameRequest']['legalName'] == 'Holding Business Ltd.'
    assert synced['amalgamationApplication']['offices'] == aml['offices']
    assert synced['amalgamationApplication']['parties'] == aml['parties']
    assert synced['amalgamationApplication']['shareStructure'] == aml['shareStructure']
    assert synced['amalgamationApplication']['amalgamatingBusinesses'] == aml['amalgamatingBusinesses']


def test_get_completed_filings_for_colin_cod_relationships(session, client, jwt):
    """Assert a relationships-shaped COD is down-converted to the legacy directors shape."""
    identifier = 'BC7654322'
    b = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value)
    factory_business_mailing_address(b)

    # a previous completed filing whose revision window will contain the existing directors
    prev_filing = factory_completed_filing(b, ANNUAL_REPORT)

    def _create_director(first_name, last_name, street):
        officer = {
            'firstName': first_name,
            'lastName': last_name,
            'middleInitial': '',
            'partyType': 'person',
            'organizationName': ''
        }
        party_role = factory_party_role(
            factory_address(street, 'delivery'),
            factory_address(street, 'mailing'),
            officer,
            prev_filing.effective_date,
            None,
            PartyRole.RoleTypes.DIRECTOR
        )
        b.party_roles.append(party_role)
        b.save()
        return party_role.party_id

    removed_party_id = _create_director('Peter', 'Griffin', 'old removed st')
    renamed_party_id = _create_director('Joe', 'Swanson', 'old renamed st')
    edited_party_id = _create_director('Jane', 'Smith', 'old edited st')
    noop_party_id = _create_director('Cleveland', 'Brown', 'old noop st')

    # pin the previous filing's revision window to include the directors created above
    prev_filing.transaction_id = VersioningProxy.get_transaction_id(db.session()) - 1
    prev_filing.save()

    def _address(street):
        return {
            'streetAddress': street,
            'addressCity': 'Victoria',
            'addressRegion': 'BC',
            'addressCountry': 'CA',
            'postalCode': 'V8W1P6'
        }

    def _relationship(given, family, street, party_id=None, actions=None, cessation_date=None,
                      address_builder=None):
        address = (address_builder or _address)(street)
        relationship = {
            'entity': {'givenName': given, 'familyName': family},
            'deliveryAddress': copy.deepcopy(address),
            'mailingAddress': copy.deepcopy(address),
            'roles': [{
                'roleType': 'Director',
                'appointmentDate': '2020-01-01',
                'cessationDate': cessation_date
            }]
        }
        if party_id is not None:
            relationship['entity']['identifier'] = str(party_id)
        if actions is not None:
            relationship['actions'] = actions
        return relationship

    def _stored_address(street):
        # mirrors the factory_address fields so the no-op director's address diff is empty
        return {
            'streetAddress': street,
            'addressCity': 'Test City',
            'addressRegion': 'BC',
            'addressCountry': 'TA',
            'postalCode': 'T3S3T3'
        }

    cod_filing_json = copy.deepcopy(FILING_HEADER)
    cod_filing_json['filing']['header']['name'] = 'changeOfDirectors'
    cod_filing_json['filing']['business']['identifier'] = identifier
    cod_filing_json['filing']['business']['legalType'] = 'BC'
    cod_filing_json['filing']['changeOfDirectors'] = {
        'relationships': [
            _relationship('Glenn', 'Quagmire', 'new appointed st', actions=['ADDED']),
            _relationship('Peter', 'Griffin', 'old removed st', party_id=removed_party_id,
                          actions=['REMOVED'], cessation_date='2020-06-01'),
            _relationship('Joseph', 'Swanson', 'old renamed st', party_id=renamed_party_id,
                          actions=['NAME_CHANGED']),
            # no actions: name matches the stored director, address differs -> derived addressChanged
            _relationship('Jane', 'Smith', 'new edited st', party_id=edited_party_id),
            # no actions and nothing changed -> empty actions, skipped by the colin-api
            _relationship('Cleveland', 'Brown', 'old noop st', party_id=noop_party_id,
                          address_builder=_stored_address)
        ]
    }
    cod_filing = factory_completed_filing(b, cod_filing_json)
    assert cod_filing.status == Filing.Status.COMPLETED.value

    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    synced = next(f for f in rv.json.get('filings') if f['filingId'] == cod_filing.id)

    cod_body = synced['filing']['changeOfDirectors']
    assert 'relationships' not in cod_body
    directors = cod_body['directors']
    assert len(directors) == 5

    added, removed, renamed, edited, noop = directors
    assert added['actions'] == ['appointed']
    assert added['officer']['firstName'] == 'Glenn'
    assert added['appointmentDate'] == '2020-01-01'
    assert 'id' not in added['officer']

    assert removed['actions'] == ['ceased']
    assert removed['officer']['id'] == removed_party_id
    assert removed['cessationDate'] == '2020-06-01'

    assert renamed['actions'] == ['nameChanged']
    assert renamed['officer']['firstName'] == 'Joseph'
    assert renamed['officer']['prevFirstName'] == 'Joe'
    assert renamed['officer']['prevLastName'] == 'Swanson'

    assert edited['actions'] == ['addressChanged']
    assert edited['officer'].get('prevFirstName') is None

    assert noop['actions'] == []
    assert noop['officer']['id'] == noop_party_id

    # the stored filing json still carries the submitted relationships shape
    assert 'relationships' in cod_filing.filing_json['filing']['changeOfDirectors']
