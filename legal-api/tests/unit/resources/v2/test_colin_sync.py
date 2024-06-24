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

import datedelta
import pytest
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CORRECTION_AR,
    CORRECTION_INCORPORATION,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
)

from legal_api.models import Business, Filing
from legal_api.services.authz import COLIN_SVC_ROLE
from tests.unit.services.utils import create_header
from tests.unit.models import factory_business_mailing_address, factory_business, factory_completed_filing, factory_filing  # noqa:E501,I001


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
    assert len(rv.json) == 1
    assert rv.json[0]['filingId'] == filing1.id


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
    assert len(rv.json) == 1
    if colin_id:
        assert rv.json[0]['filingId'] == filing.id
    else:
        assert rv.json[0]['filingId'] == incorp_filing.id


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


def test_future_filing_coa(session, client, jwt):
    """Assert that future effective filings are saved and have the correct status changes."""
    import pytz
    from tests.unit.models import factory_pending_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier, (datetime.utcnow() - datedelta.YEAR), None, Business.LegalTypes.BCOMP.value)
    factory_business_mailing_address(b)
    coa = copy.deepcopy(FILING_HEADER)
    coa['filing']['header']['name'] = 'changeOfAddress'
    coa['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['deliveryAddress']['addressCountry'] = 'CA'
    coa['filing']['changeOfAddress']['offices']['registeredOffice']['mailingAddress']['addressCountry'] = 'CA'
    coa['filing']['business']['identifier'] = identifier

    filing = factory_pending_filing(b, coa)
    filing.effective_date = datetime.utcnow() + datedelta.DAY
    filing.save()
    assert filing.status == Filing.Status.PENDING.value

    filing.payment_completion_date = pytz.utc.localize(datetime.utcnow())
    filing.save()

    assert filing.status == Filing.Status.PAID.value

    rv = client.get('/api/v2/businesses/internal/filings/PAID', headers=create_header(jwt, [COLIN_SVC_ROLE]))
    paid_filings = rv.json
    assert paid_filings[0]
    # check values that future effective filings job depends on are there
    assert paid_filings[0]['filing']['header']['filingId'] == filing.id
    assert paid_filings[0]['filing']['header']['paymentToken']
    assert paid_filings[0]['filing']['header']['effectiveDate']
