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
from datetime import datetime
from http import HTTPStatus

import pytest
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CORRECTION_AR,
    CORRECTION_COL,
    CORRECTION_COR
)

from legal_api.models import Business, Filing, PartyRole
from legal_api.models.colin_event_id import ColinEventId
from legal_api.services.authz import COLIN_SVC_ROLE
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
    # completed correction with no colin_event_ids
    assert filing6.status == Filing.Status.COMPLETED.value

    # test endpoint returned filing1 only (completed, no corrections, with no colin id set)
    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filings = rv.json.get('filings')
    assert len(filings) == 2
    assert filings[0]['filingId'] == filing1.id
    assert filings[1]['filingId'] == filing6.id


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
    db.session.execute(
        f"""
        insert into colin_last_update (last_update, last_event_id)
        values (current_timestamp, {colin_id})
        """
    )

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