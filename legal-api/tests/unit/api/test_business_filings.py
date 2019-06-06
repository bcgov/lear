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
from datetime import datetime
from http import HTTPStatus

from tests.unit.models.test_filing import AR_FILING, factory_business, factory_filing


def test_get_all_business_filings_only_one_in_ledger(session, client):
    """Assert that the business info can be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings')

    assert rv.status_code == 200
    assert len(rv.json.get('filings')) == 1
    assert rv.json.get('filings')[0].get('jsonSubmission') == AR_FILING


def test_get_all_business_filings_multi_in_ledger(session, client):
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

    rv = client.get(f'/api/v1/businesses/{identifier}/filings')

    assert rv.status_code == 200
    assert len(rv.json.get('filings')) == 3


def test_get_one_business_filing_by_id(session, client):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    assert rv.status_code == 200
    assert rv.json == AR_FILING


def test_get_one_business_filing_by_id_missing_id(session, client):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id + 1}')

    assert rv.status_code == 404
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_get_filing_no_business(session, client):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings_id}')

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_post_invalid_filing_id(session, client):
    """Assert that a filing cannot be created against a given filing_id."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                     json=AR_FILING)

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json == {'message':
                       f'Illegal to attempt to create a new filing over an existing filing for {identifier}.'}


def test_post_filing_no_business(session, client):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.post(f'/api/v1/businesses/{identifier}/filings/{filings_id}',
                     json=AR_FILING)

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_post_empty_ar_filing_to_a_business(session, client):
    """Assert that an empty filing cannot be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=None)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json == {'message': f'No filing json data in body of post for {identifier}.'}


def test_post_ar_not_paid_filing_to_a_business(session, client):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING)

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json == AR_FILING


def test_post_ar_paid_filing_to_a_business(session, client):
    """Assert that a paid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar)

    assert rv.status_code == HTTPStatus.CREATED
    assert rv.json == ar


def test_post_ar_paid_invalid_filing_to_a_business(session, client):
    """Assert that a paid filing can be posted."""
    import copy
    identifier = 'CP7654321'
    factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'
    ar['filing'].pop('business')

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=ar)

    assert rv.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert rv.json['message'].startswith('Invalid filing:')


def test_update_ar_filing_to_a_business(session, client):
    """Assert that a filing can be updated if not paid."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['date'] = '2019-07-01'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar)

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json == ar


def test_update_ar_to_paid_filing_to_a_business(session, client):
    """Assert that a valid filing can be updated to a paid filing."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar)

    assert rv.status_code == HTTPStatus.ACCEPTED
    assert rv.json == ar


def test_update_block_ar_update_to_a_paid_filing_to_a_business(session, client):
    """Assert that a valid filing can NOT be updated once it has been paid."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'
    filings = factory_filing(b, ar)

    ar['filing']['header'].pop('paymentToken', None)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id}',
                    json=ar)

    assert rv.status_code == HTTPStatus.FORBIDDEN
    assert rv.json == {'message': 'Filings cannot be changed after they are paid for and stored.'}


def test_update_ar_with_a_missing_filing_id_fails(session, client):
    """Assert that updating a missing filing fails."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar)

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_update_ar_with_a_missing_business_id_fails(session, client):
    """Assert that updating to a non-existant business fails."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['paymentToken'] = 'token'

    identifier = 'CP0000001'

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=ar)

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_update_ar_with_missing_json_body_fails(session, client):
    """Assert that updating a filing with no JSON body fails."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    rv = client.put(f'/api/v1/businesses/{identifier}/filings/{filings.id+1}',
                    json=None)

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json == {'message': f'No filing json data in body of post for {identifier}.'}
