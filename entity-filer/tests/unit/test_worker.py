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
"""The Test Suites to ensure that the worker is operating correctly."""
import datetime
import json
import random

import pytest

from tests import EPOCH_DATETIME
from tests.unit import AR_FILING, COA_FILING, COMBINED_FILING, create_business, create_filing


def test_extract_payment_token():
    """Assert that the payment token can be extracted from the Queue delivered Msg."""
    from entity_filer.worker import extract_payment_token
    from stan.aio.client import Msg
    import stan.pb.protocol_pb2 as protocol

    token = {'paymentToken': {'id': 1234, 'statusCode': 'COMPLETED'}}

    msg = Msg()
    msg.proto = protocol.MsgProto
    msg.proto.data = json.dumps(token).encode('utf-8')

    assert extract_payment_token(msg) == token


def test_get_filing_by_payment_id(app, session):
    """Assert that a unique filling gets retrieved for a payment_id."""
    from entity_filer.worker import get_filing_by_payment_id

    payment_id = str(random.SystemRandom().getrandbits(0x58))

    create_filing(payment_id)

    filing = get_filing_by_payment_id(str(payment_id))

    assert filing
    assert filing.payment_token == payment_id


def test_process_filing_missing_app(app, session):
    """Assert that a filling will fail with no flask app supplied."""
    from entity_filer.worker import process_filing
    from legal_api.models import Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    with pytest.raises(Exception):
        process_filing(payment_token, flask_app=None)


def test_process_ar_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(AR_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert business.last_ar_date.replace(tzinfo=None) == EPOCH_DATETIME


def test_process_coa_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    new_delivery_address = COA_FILING['filing']['changeOfAddress']['deliveryAddress']
    new_mailing_address = COA_FILING['filing']['changeOfAddress']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, COA_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value

    delivery_address = business.delivery_address.one_or_none().json
    for key in delivery_address.keys():
        if key != 'addressType':
            assert delivery_address[key] == new_delivery_address[key]

    mailing_address = business.mailing_address.one_or_none().json
    for key in mailing_address.keys():
        if key != 'addressType':
            assert mailing_address[key] == new_mailing_address[key]


def test_process_combined_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(COMBINED_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))
    new_delivery_address = COMBINED_FILING['filing']['changeOfAddress']['deliveryAddress']
    new_mailing_address = COMBINED_FILING['filing']['changeOfAddress']['mailingAddress']

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, COMBINED_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.COMPLETED.value
    print(business.json())
    print(business.last_agm_date)
    print(agm_date)
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert business.last_ar_date.replace(tzinfo=None) == EPOCH_DATETIME

    delivery_address = business.delivery_address.one_or_none().json
    for key in delivery_address.keys():
        if key != 'addressType':
            assert delivery_address[key] == new_delivery_address[key]

    mailing_address = business.mailing_address.one_or_none().json
    for key in mailing_address.keys():
        if key != 'addressType':
            assert mailing_address[key] == new_mailing_address[key]


def test_process_filing_failed(app, session):
    """Assert that an AR filling status is set to error if payment transaction failed."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business, Filing

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    business_id = business.id
    create_filing(payment_id, AR_FILING, business.id)
    payment_token = {'paymentToken': {'id': payment_id, 'statusCode': 'TRANSACTION_FAILED'}}

    # TEST
    process_filing(payment_token, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.business_id == business_id
    assert filing.status == Filing.Status.ERROR.value
    assert not business.last_agm_date
    assert not business.last_ar_date
