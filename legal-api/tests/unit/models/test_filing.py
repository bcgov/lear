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

"""Tests to assure the Filing Model.

Test-Suite to ensure that the Business Model is working as expected.
"""
import datetime
import json
from http import HTTPStatus

import pytest
from flask import current_app
from sqlalchemy_continuum import versioning_manager

from legal_api.exceptions import BusinessException
from legal_api.models import Filing, User
from tests import EPOCH_DATETIME
from tests.unit.models import AR_FILING, factory_business, factory_filing


def test_minimal_filing_json(session):
    """Assert that a minimal filing can be created."""
    b = factory_business('CP1234567')

    data = {'filing': 'not a real filing, fail validation'}

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()

    assert filing.id is not None


def test_filing_block_orm_delete(session):
    """Assert that attempting to delete a filing will raise a BusinessException."""
    from legal_api.exceptions import BusinessException

    b = factory_business('CP1234567')

    data = {'filing': 'not a real filing, fail validation'}

    filing = Filing()
    filing.business_id = b.id
    filing.filing_date = datetime.datetime.utcnow()
    filing.filing_data = json.dumps(data)
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        session.delete(filing)
        session.commit()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_json(session):
    """Assert that an AR filing can be saved."""
    import copy
    b = factory_business('CP1234567')
    filing = factory_filing(b, AR_FILING)

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header']['filingId'] = filing.id
    ar['filing']['header']['colinId'] = None

    assert filing.id
    assert filing.json['filing']['business'] == AR_FILING['filing']['business']
    assert filing.json['filing']['annualReport'] == AR_FILING['filing']['annualReport']


def test_filing_delete_is_blocked(session):
    """Assert that an AR filing can be saved."""
    b = factory_business('CP1234567')
    filing = factory_filing(b, AR_FILING)

    with pytest.raises(BusinessException) as excinfo:
        filing.delete()

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN
    assert excinfo.value.error == 'Deletion not allowed.'


def test_filing_missing_name(session):
    """Assert that an AR filing can be saved."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)
    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header'].pop('name', None)

    with pytest.raises(BusinessException) as excinfo:
        factory_filing(b, ar)

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert excinfo.value.error == 'No filings found.'


def test_filing_dump_json(session):
    """Assert the filing json serialization works correctly."""
    import copy
    identifier = 'CP7654321'
    b = factory_business(identifier)

    # Check base JSON
    filings = factory_filing(b, AR_FILING)

    assert filings.json['filing']['business'] == AR_FILING['filing']['business']
    assert filings.json['filing']['annualReport'] == AR_FILING['filing']['annualReport']

    # Check payment token
    ar = copy.deepcopy(AR_FILING)
    token = 'token'
    ar['filing']['header']['paymentToken'] = token
    filings = factory_filing(b, ar)
    assert filings.json['filing']['header']['paymentToken'] == token

    # check submitter
    u = User()
    u.username = 'submitter'
    u.save()
    ar = copy.deepcopy(AR_FILING)
    filings = factory_filing(b, ar)
    filings.submitter_id = u.id
    filings.save()
    assert filings.json['filing']['header']['submitter'] == u.username

    # check Exception
    ar = copy.deepcopy(AR_FILING)
    filings = factory_filing(b, ar)
    filings.save()
    filings.submitter_id = -1  # some bogus id to throw an error
    with pytest.raises(KeyError):
        filings.json()


def test_filing_save_to_session(session):
    """Assert that the filing is saved to the session but not committed."""
    from sqlalchemy.orm.session import Session
    # b = factory_business('CP1234567')
    # filing = factory_filing(b, AR_FILING)

    filing = Filing()

    assert not session.new
    assert not Session.object_session(filing)

    filing.save_to_session()

    assert filing.id is None
    assert session.new
    assert Session.object_session(filing)


def test_add_json_after_payment(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME

    # sanity check starting value
    assert not filing.status

    filing.payment_token = 'payment token'
    filing.filing_json = AR_FILING

    assert filing.json
    assert filing.status == Filing.Status.PENDING.value


def test_add_json_and_payment_after_saved_filing(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.save()

    # sanity check starting value
    assert filing.status == Filing.Status.DRAFT.value

    filing.payment_token = 'payment token'
    filing.filing_json = AR_FILING

    assert filing.json
    assert filing.status == Filing.Status.PENDING.value


def test_add_payment_completion_date_after_payment(session):
    """Assert that the json can be added in the same session that a paymentToken was applied."""
    filing = Filing()
    filing.filing_date = EPOCH_DATETIME
    filing.save()

    filing.payment_token = 'payment token'
    filing.filing_json = AR_FILING

    # sanity check starting position
    assert filing.json
    assert filing.status == Filing.Status.PENDING.value

    filing.payment_completion_date = EPOCH_DATETIME
    print(filing.status)
    assert filing.status == Filing.Status.COMPLETED.value


def test_add_invalid_json_after_payment(session):
    """Assert that a filing_json has to be valid if a payment token has been set."""
    import copy
    filing = Filing()
    filing.payment_token = 'payment token'

    ar = copy.deepcopy(AR_FILING)
    ar['filing']['header'].pop('date', None)

    with pytest.raises(BusinessException) as excinfo:
        filing.filing_json = ar

    assert excinfo.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_updating_payment_token_fails(session):
    """Assert that a payment token cannot be updated."""
    filing = Filing()
    filing.payment_token = 'payment token'
    filing.save()

    with pytest.raises(BusinessException) as excinfo:
        filing.payment_token = 'payment token'

    assert excinfo.value.status_code == HTTPStatus.FORBIDDEN


def test_updating_filing_with_payment_token(session):
    """Assert that a payment token can be applied to an existing filing."""
    from tests.conftest import not_raises
    filing = Filing()
    filing.save()

    with not_raises(BusinessException):
        filing.payment_token = 'payment token'


def test_get_legal_filings():
    """Assert that the legal_filings member returns valid JSON Legal Filing segments."""
    filing = Filing()

    assert not filing.legal_filings()

    filing.filing_json = AR_FILING
    legal_filings = filing.legal_filings()

    assert legal_filings
    assert 'annualReport' in legal_filings[0].keys()


def test_get_filing_by_payment_token(session):
    """Assert that a filing can be retrieved by a unique payment token."""
    payment_token = '1000'
    filing = Filing()
    filing.filing_json = AR_FILING
    filing.payment_token = payment_token
    filing.save()

    rv = Filing.get_filing_by_payment_token(payment_token)

    assert rv
    assert rv.payment_token == payment_token


def test_get_filings_by_status(session):
    """Assert that a filing can be retrieved by status."""
    uow = versioning_manager.unit_of_work(session)
    transaction = uow.create_transaction(session)
    business = factory_business('CP1234567')
    payment_token = '1000'
    filing = Filing()
    filing.business_id = business.id
    filing.filing_json = AR_FILING
    filing.payment_token = payment_token
    filing.transaction_id = transaction.id
    filing.payment_completion_date = datetime.datetime.utcnow()
    filing.save()

    rv = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])

    assert rv
    assert rv[0].status == Filing.Status.COMPLETED.value


# testdata pattern is ({str: environment}, {expected return value})
TEST_FILING_GO_LIVE_DATE = [
    ('filing returned', 10, 'rv is not None', Filing.Status.COMPLETED.value),
    ('no filing returned', -10, 'rv == []', None),
]


@pytest.mark.parametrize('test_type,days,expected,status', TEST_FILING_GO_LIVE_DATE)
def test_get_filings_by_status_before_go_live_date(session, test_type, days, expected, status):
    """Assert that a filing can be retrieved by status."""
    import copy
    uow = versioning_manager.unit_of_work(session)
    transaction = uow.create_transaction(session)
    business = factory_business('CP1234567')
    payment_token = '1000'
    ar = copy.deepcopy(AR_FILING)

    go_live_date = datetime.date.fromisoformat(current_app.config.get('GO_LIVE_DATE'))
    filing_date = go_live_date + datetime.timedelta(days=days)

    filing = Filing()
    filing.filing_date = filing_date
    filing.business_id = business.id
    filing.filing_json = ar
    filing.payment_token = payment_token
    filing.transaction_id = transaction.id
    filing.payment_completion_date = datetime.datetime.utcnow()
    filing.save()

    rv = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value], go_live_date)

    assert eval(expected)  # pylint: disable=eval-used; useful for parameterized tests
    if rv:
        assert rv[0].status == status


def test_get_internal_filings(session, client, jwt):
    """Assert that the get_completed_filings_for_colin returns completed filings with no colin ids set."""
    from legal_api.models import Filing
    from tests.unit.models import factory_completed_filing
    # setup
    identifier = 'CP7654321'
    b = factory_business(identifier)
    filing = factory_completed_filing(b, AR_FILING)
    assert filing.status == Filing.Status.COMPLETED.value
    filing.colin_event_id = 1234
    filing.save()
    filings = Filing.get_completed_filings_for_colin()

    # test method
    # assert doesn't return completed filing with colin_event_ids set
    assert len(filings) == 0
    # assert returns completed filings with colin_event_id not set
    filing.colin_event_id = None
    filing.save()
    filings = Filing.get_completed_filings_for_colin()
    assert len(filings) == 1
    assert filing.id == filings[0].json['filing']['header']['filingId']
    assert filings[0].json['filing']['header']['colinId'] is None
    # assert doesn't return non completed filings
    filing.transaction_id = None
    filing.save()
    assert filing.status != Filing.Status.COMPLETED.value
    filings = Filing.get_completed_filings_for_colin()
    assert len(filings) == 0
