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

from flask import current_app

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests.unit.models import AR_FILING, factory_business, factory_business_mailing_address, factory_filing
from tests.unit.services.utils import create_header


def test_get_all_business_filings_only_one_in_ledger(session, client):
    """Assert that the business info can be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    print('test_get_all_business_filings - filing:', filings)

    rv = client.get(f'/api/v1/businesses/{identifier}/filings')

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 1
    assert rv.json.get('filings')[0] == ar


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

    assert rv.status_code == HTTPStatus.OK
    assert len(rv.json.get('filings')) == 3


def test_get_one_business_filing_by_id(session, client):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['filingId'] = filings.id
    ar['filing']['header']['colinId'] = None

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    assert rv.status_code == HTTPStatus.OK
    assert rv.json == ar


def test_get_404_when_business_invalid_filing_id(session, client):
    """Assert that the business info cannot be received in a valid JSONSchema format."""
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filings = factory_filing(b, AR_FILING)

    print('test_get_one_business_filing - filing:', filings)

    print(f'/api/v1/businesses/{identifier}/filings/{filings.id}')

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings.id + 1}')

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} no filings found'}


def test_get_404_filing_with_invalid_business(session, client):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'
    filings_id = 1

    rv = client.get(f'/api/v1/businesses/{identifier}/filings/{filings_id}')

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
    assert rv.json == {'message':
                       f'Illegal to attempt to create a new filing over an existing filing for {identifier}.'}


def test_post_filing_no_business(session, client, jwt):
    """Assert that a filing cannot be created against non-existent business."""
    identifier = 'CP7654321'

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f'{identifier} not found'}


def test_post_empty_ar_filing_to_a_business(session, client, jwt):
    """Assert that an empty filing cannot be posted."""
    identifier = 'CP7654321'
    factory_business(identifier)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=None,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json == {'message': f'No filing json data in body of post for {identifier}.'}


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
    assert rv.json['errors'][0]['path'] == 'filing/header'
    assert rv.json['errors'][0]['error'] == "'name' is a required property"


def test_post_valid_ar(session, client, jwt):
    """Assert that a unpaid filing can be posted."""
    identifier = 'CP7654321'
    business = factory_business(identifier)
    factory_business_mailing_address(business)

    rv = client.post(f'/api/v1/businesses/{identifier}/filings',
                     json=AR_FILING,
                     headers=create_header(jwt, [STAFF_ROLE], identifier)
                     )

    assert rv.status_code == HTTPStatus.CREATED
    assert not rv.json.get('errors')
    assert rv.json['filing']['header']['filingId']
    assert rv.json['filing']['header']['paymentToken']
    assert rv.json['filing']['header']['paymentToken'] == '153'


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
    assert not rv.json.get('errors')


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
    assert rv.json == {'message': 'Filings cannot be changed after they are paid for and stored.'}


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
    assert rv.json == {'message': f'{identifier} no filings found'}


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
    assert rv.json == {'message': f'{identifier} not found'}


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
    assert rv.json == {'message': f'No filing json data in body of post for {identifier}.'}


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
