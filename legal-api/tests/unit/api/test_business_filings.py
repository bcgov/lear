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
import asyncio
import json
from datetime import datetime
from http import HTTPStatus

import dpath.util
import pytest
from flask import current_app

from legal_api.services import QueueService
from legal_api.services.authz import BASIC_USER, COLIN_SVC_ROLE, STAFF_ROLE
from tests import integration_nats, integration_payment
from tests.unit.models import AR_FILING, factory_business, factory_business_mailing_address, factory_filing
from tests.unit.services.utils import create_header


def test_get_all_business_filings_only_one_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0  # The endpoint will return only completed filings


def test_get_all_business_filings_multi_in_ledger(session, client, jwt):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    from tests import add_years

    ar = copy.deepcopy(AR_FILING)
    identifier = 'CP7654321'

    # create business
    b = factory_business(identifier)

    # add 3 filings, add a year onto the AGM date
    for i in range(0, 3):
        ar['filing']['annualReport']['annualGeneralMeetingDate'] = \
            datetime.date(add_years(datetime(2001, 8, 5, 7, 7, 58, 272362), i)).isoformat()
        factory_filing(b, ar)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 0


def test_get_one_business_filing_by_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert rv.json['filing']['business'] == ar['filing']['business']


def test_get_404_when_business_invalid_filing_id(session, client, jwt):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id + 1}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_get_404_filing_with_invalid_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings_id}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_post_fail_if_given_filing_id(session, client, jwt):
    """Assert that a filing cannot be created against a given filing_id."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json['errors'][0] == {'message':
                                    f'Illegal to attempt to create a duplicate filing for {identifier}.'}


def test_post_filing_no_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['errors'][0] == {'message': f'{identifier} not found'}


def test_post_empty_ar_filing_to_a_business(session, client, jwt):
    """Assert that an empty filing cannot be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=None,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


def test_post_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED


def test_post_not_authorized_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
                     json=AR_FILING,
                     headers=create_header(jwt, [BASIC_USER], 'WRONGUSER')
                     )

    assert rv.status_code == HTTPStatus.UNAUTHORIZED


def test_post_draft_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?draft=true',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json['filing']['header'].get('paymentToken')
    assert rv.json['filing']['header']['filingId']


def test_post_only_validate_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('errors')


def test_post_only_validate_error_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header'].pop('name')

    rv = client.post(f'/api/v1/businesses/{identifier}/filings?only_validate=true',
                     json=ar,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['error'] == "'name' is a required property"


@integration_payment
def test_post_valid_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    from legal_api.models import Address, Filing
    identifier = 'CP7654321'
    business = factory_business(identifier)
    mailing_address = Address(city='Test Mailing City', address_type=Address.MAILING)
    business.mailing_address.append(mailing_address)
    business.save()

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    # check return
    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']
    assert rv.json['filing']['header']['paymentToken'] == '153'

    # check stored filing
    filing = Filing.get_filing_by_payment_token(rv.json['filing']['header']['paymentToken'])
    assert filing
    assert filing.status == Filing.Status.PENDING.value


def test_post_valid_ar_failed_payment(monkeypatch, session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_business_mailing_address(business)

    old_svc = current_app.config.get('PAYMENT_SVC_URL')
    current_app.config['PAYMENT_SVC_URL'] = 'http://nowhere.localdomain'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    current_app.config['PAYMENT_SVC_URL'] = old_svc
    assert rv.status_code == HTTPStatus.PAYMENT_REQUIRED
    assert rv.json.get('errors')
    assert rv.json['errors'][0]['message'] == 'unable to create invoice for payment.'


@integration_payment
def test_update_ar_filing_to_a_business(session, client, jwt):
    """Assert that a filing can be updated if not paid."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['date'] = '2001-08-05'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    ar['filing']['header']['submitter'] = identifier
    ar['filing']['header']['date'] = rv.json['filing']['header']['date']
    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['business'] == ar['filing']['business']
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['submitter']
    assert rv.json['filing']['header']['paymentToken']


def test_update_draft_ar(session, client, jwt):
    """Assert that a valid filing can be updated to a paid filing."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}?draft=true',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['business'] == ar['filing']['business']
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert not rv.json['filing']['header'].get('paymentToken')
    assert rv.json['filing']['header']['filingId'] == filings.id


def test_update_block_ar_update_to_a_paid_filing(session, client, jwt):
    """Assert that a valid filing can NOT be updated once it has been paid."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    filings = factory_filing(b, ar)

    filings.payment_token = 'token'
    filings.save()

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json['errors'][0] == {'error': 'Filings cannot be changed after the invoice is created.'}


def test_update_ar_with_a_missing_filing_id_fails(session, client, jwt):
    """Assert that updating a missing filing fails."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['errors'][0] == {'message': f'{identifier} no filings found'}


def test_update_ar_with_a_missing_business_id_fails(session, client, jwt):
    """Assert that updating to a non-existant business fails."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    identifier = 'CP0000001'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json['errors'][0] == {'message': f'{identifier} not found'}


def test_update_ar_with_missing_json_body_fails(session, client, jwt):
    """Assert that updating a filing with no JSON body fails."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=None,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json['errors'][0] == {'message': f'No filing json data in body of post for {identifier}.'}


# @integration_nats
# @pytest.mark.asyncio
# async def test_colin_filing_to_queue(app_ctx, session, client, jwt, stan_server, event_loop):
#     """Assert that payment tokens can be retrieved and decoded from the Queue."""
#     import copy
#     # SETUP
#     msgs = []
#     this_loop = asyncio.get_event_loop()
#     # this_loop = event_loop
#     future = asyncio.Future(loop=this_loop)
#     queue = QueueService(app_ctx, this_loop)
#     await queue.connect()

#     async def cb(msg):
#         nonlocal msgs
#         nonlocal future
#         msgs.append(msg)
#         if len(msgs) == 5:
#             future.set_result(True)

#     await queue.stan.subscribe(subject=queue.subject,
#                                queue='colin_queue',
#                                durable_name='colin_queue',
#                                cb=cb)

#     # TEST - add some COLIN filings to the system, check that they got placed on the Queue
#     for i in range(0, 5):
#         # Create business
#         identifier = f'CP765432{i}'
#         b = factory_business(identifier)
#         factory_business_mailing_address(b)
#         # Create anm AR filing for the business
#         ar = copy.deepcopy(AR_FILING)
#         ar['filing']['header']['colinId'] = 1230 + i
#         ar['filing']['business']['identifier'] = identifier

#         # POST the AR
#         rv = client.post(f'/api/v1/businesses/{identifier}/filings',
#                          json=ar,
#                          headers=create_header(jwt, [COLIN_SVC_ROLE], 'colin_service')
#                          )

#         # Assure that the filing was accepted
#         assert rv.status_code == HTTPStatus.CREATED

#     # Await all the messages were received
#     try:
#         await asyncio.wait_for(future, 2, loop=this_loop)
#     except Exception as err:
#         print(err)

#     # CHECK the colinFilings were retrieved from the queue
#     assert len(msgs) == 5
#     for i in range(0, 5):
#         m = msgs[i]
#         assert 'colinFiling' in m.data.decode('utf-8')
#         assert 1230 + i == dpath.util.get(json.loads(m.data.decode('utf-8')),
#                                           'colinFiling/id')


@integration_nats
@pytest.mark.asyncio
async def test_colin_filing_failed_to_queue(app_ctx, session, client, jwt, stan_server, event_loop):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    import copy
    # SETUP
    this_loop = asyncio.get_event_loop()
    this_loop = event_loop
    queue = QueueService(app_ctx, this_loop)
    await queue.connect()

    # TEST - add some COLIN filings to the system, check that they got placed on the Queue
    # Create business
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    # Create an AR filing for the business
    ar = copy.deepcopy(AR_FILING)
    # ar['filing']['header']['colinId']
    ar['filing']['business']['identifier'] = identifier

    # POST the AR
    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar,
                     headers=create_header(jwt, [COLIN_SVC_ROLE], 'colin_service')
                     )

    # Assure that the filing was accepted
    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert 'missing filing/header/colinId' in rv.json['errors']['message']


@integration_nats
# @pytest.mark.asyncio
def test_colin_filing_to_queue(app_ctx, session, client, jwt, stan_server):
    """Assert that payment tokens can be retrieved and decoded from the Queue."""
    import copy
    # SETUP
    msgs = []
    this_loop = asyncio.get_event_loop()
    # this_loop = event_loop
    future = asyncio.Future(loop=this_loop)
    queue = QueueService(app_ctx, this_loop)
    this_loop.run_until_complete(queue.connect())

    async def cb(msg):
        nonlocal msgs
        nonlocal future
        msgs.append(msg)
        if len(msgs) == 5:
            future.set_result(True)

    this_loop.run_until_complete(queue.stan.subscribe(subject=queue.subject,
                                                      queue='colin_queue',
                                                      durable_name='colin_queue',
                                                      cb=cb))

    # TEST - add some COLIN filings to the system, check that they got placed on the Queue
    for i in range(0, 5):
        # Create business
        identifier = f'CP765432{i}'
        b = factory_business(identifier)
        factory_business_mailing_address(b)
        # Create anm AR filing for the business
        ar = copy.deepcopy(AR_FILING)
        ar['filing']['header']['colinId'] = 1230 + i
        ar['filing']['business']['identifier'] = identifier

        # POST the AR
        rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                         json=ar,
                         headers=create_header(jwt, [COLIN_SVC_ROLE], 'colin_service')
                         )

        # Assure that the filing was accepted
        assert rv.status_code == HTTPStatus.CREATED

    # Await all the messages were received
    try:
        this_loop.run_until_complete(asyncio.wait_for(future, 2, loop=this_loop))
    except Exception as err:
        print(err)

    # CHECK the colinFilings were retrieved from the queue
    assert len(msgs) == 5
    for i in range(0, 5):
        m = msgs[i]
        assert 'colinFiling' in m.data.decode('utf-8')
        assert 1230 + i == dpath.util.get(json.loads(m.data.decode('utf-8')),
                                          'colinFiling/id')


@integration_payment
def test_update_ar_with_colin_id_set(session, client, jwt):
    """Assert that when a filing with colinId set (as when colin updates legal api) that colin_event_id is set."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)

    filings = factory_filing(b, AR_FILING)

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['colinId'] = 1234

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar,
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json['filing']['business'] == ar['filing']['business']
    assert rv.json['filing']['annualReport'] == ar['filing']['annualReport']
    assert not rv.json['filing']['header'].get('colinId')
    assert rv.json['filing']['header']['filingId'] == filings.id


def test_get_internal_filings(session, client, jwt):
    """Assert that the internal filings get endpoint returns all completed filings without colin ids."""
    from legal_api.models import Filing
    from tests.unit.models import factory_completed_filing, factory_error_filing, factory_pending_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)

    filing1 = factory_completed_filing(b, AR_FILING)
    filing2 = factory_completed_filing(b, AR_FILING)
    filing3 = factory_pending_filing(b, AR_FILING)
    filing4 = factory_filing(b, AR_FILING)
    filing5 = factory_error_filing(b, AR_FILING)

    assert filing1.status == Filing.Status.COMPLETED.value
    # completed with colin_event_id
    filing2.colin_event_id = 1234
    filing2.save()
    assert filing2.status == Filing.Status.COMPLETED.value
    assert filing2.colin_event_id is not None
    # pending with no colin_event_id
    assert filing3.status == Filing.Status.PENDING.value
    # draft with no colin_event_id
    assert filing4.status == Filing.Status.DRAFT.value
    # error with no colin_event_id
    assert filing5.status == Filing.Status.ERROR.value

    # test endpoint returned filing1 only (completed with no colin id set)
    rv = client.get(f'/api/v1/businesses/internal/filings')
    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json) == 1
    assert rv.json[0]['filing']['header']['filingId'] == filing1.id


def test_patch_internal_filings(session, client, jwt):
    """Assert that the internal filings patch endpoint updates the colin_event_id."""
    from legal_api.models import Filing
    from tests.unit.models import factory_completed_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing = factory_completed_filing(b, AR_FILING)
    colin_id = 1234

    # make request
    rv = client.patch(f'/api/v1/businesses/internal/filings/{filing.id}',
                      json={'colinId': colin_id},
                      headers=create_header(jwt, [COLIN_SVC_ROLE])
                      )

    # test result
    filing = Filing.find_by_id(filing.id)
    assert rv.status_code == HTTPStatus.ACCEPTED
    assert filing.colin_event_id == colin_id
    assert rv.json['filing']['header']['filingId'] == filing.id
    assert rv.json['filing']['header']['colinId'] == colin_id


def test_get_colin_id(session, client, jwt):
    """Assert the internal/filings/colin_id get endpoint returns properly."""
    from tests.unit.models import factory_completed_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    factory_business_mailing_address(b)
    filing = factory_completed_filing(b, AR_FILING)
    colin_event_id = 1234
    filing.colin_event_id = colin_event_id
    filing.save()

    rv = client.get(f'/api/v1/businesses/internal/filings/colin_id/{colin_event_id}')
    assert rv.status_code == HTTPStatus.OK
    assert rv.json == {'colinId': colin_event_id}

    rv = client.get(f'/api/v1/businesses/internal/filings/colin_id/{1}')
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

    rv = client.get(f'/api/v1/businesses/internal/filings/colin_id')
    assert rv.status_code == HTTPStatus.OK
    assert rv.json == {'maxId': colin_id}


def test_post_colin_last_update(session, client, jwt):
    """Assert the internal/filings/colin_id post endpoint updates the colin_last_update table."""
    colin_id = 1234
    rv = client.post(f'/api/v1/businesses/internal/filings/colin_id/{colin_id}',
                     headers=create_header(jwt, [COLIN_SVC_ROLE])
                     )
    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json == {'maxId': colin_id}
