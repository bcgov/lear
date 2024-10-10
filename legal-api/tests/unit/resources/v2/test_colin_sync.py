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

import pytest
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CORRECTION_AR,
    CORRECTION_INCORPORATION,
    INCORPORATION_FILING_TEMPLATE,
)

from legal_api.models import Batch, BatchProcessing, Business, Filing
from legal_api.services.authz import COLIN_SVC_ROLE
from tests.unit.services.utils import create_header
from tests.unit.models import (
    factory_business,
    factory_business_mailing_address,
    factory_completed_filing,
    factory_filing,
)


def test_get_internal_filings(session, client, jwt):
    """Assert that the internal filings get endpoint returns all completed filings without colin ids."""
    from legal_api.models.colin_event_id import ColinEventId
    from tests.unit.models import factory_error_filing, factory_pending_filing
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
    assert len(filings) == 1
    assert filings[0]['filingId'] == filing1.id


@pytest.mark.parametrize(
        'test_name,step,event_id,expected', [
            ("D1_NOT_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1, None, True),
            ("D1_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1, 12345, False),
            ("D2_NOT_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2, None, True),
            ("D2_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2, 12345, False),
            ("D3_NOT_SYNCED", BatchProcessing.BatchProcessingStep.DISSOLUTION, None, False),
            ("D3_ALREADY_SYNCED", BatchProcessing.BatchProcessingStep.DISSOLUTION, 12345, False),
        ]
)
def test_get_internal_batch_processings(session, client, jwt, test_name, step, event_id, expected):
    """Assert that the internal batch processings get endpoint returns all eligible batch processings."""
    from legal_api.models.colin_event_id import ColinEventId
    from tests.unit.models import factory_batch, factory_batch_processing

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    batch = factory_batch(status=Batch.BatchStatus.PROCESSING)
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
        step=step
    )
    if event_id:
        colin_event_id = ColinEventId()
        colin_event_id.colin_event_id = event_id
        colin_event_id.batch_processing_id = batch_processing.id
        colin_event_id.batch_processing_step = batch_processing.step
        colin_event_id.save()

    # Test
    rv = client.get('/api/v2/businesses/internal/batch_processings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))   
    assert rv.status_code == HTTPStatus.OK 
    batch_processings = rv.json.get("batch_processings")
    if expected:
        assert len(batch_processings) == 1
    else:
        assert len(batch_processings) == 0


@pytest.mark.parametrize('identifier, base_filing, corrected_filing, colin_id', [
    ('BC1234567', CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE, 1234),
    ('BC1234568', CORRECTION_INCORPORATION, INCORPORATION_FILING_TEMPLATE, None),
])
def test_get_bcomp_corrections(session, client, jwt, identifier, base_filing, corrected_filing, colin_id):
    """Assert that the internal filings get endpoint returns corrections for bcomps."""
    # setup
    b = factory_business(identifier=identifier, entity_type=Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)

    incorp_filing = factory_completed_filing(business=b, data_dict=corrected_filing, colin_id=colin_id)
    correction_filing = copy.deepcopy(base_filing)
    correction_filing['filing']['correction']['correctedFilingId'] = incorp_filing.id
    filing = factory_completed_filing(b, correction_filing)

    # test endpoint returns filing
    rv = client.get('/api/v2/businesses/internal/filings',
                    headers=create_header(jwt, [COLIN_SVC_ROLE]))
    assert rv.status_code == HTTPStatus.OK
    filings = rv.json.get('filings')
    assert len(filings) == 1
    if colin_id:
        assert filings[0]['filingId'] == filing.id
    else:
        assert filings[0]['filingId'] == incorp_filing.id


def test_patch_internal_filings(session, client, jwt):
    """Assert that the internal filings patch endpoint updates the colin_event_id."""
    from legal_api.models.colin_event_id import ColinEventId
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
    from legal_api.models.colin_event_id import ColinEventId
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
    from tests.unit.models import db
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
