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
from tests.unit import AR_FILING, create_business, create_filing


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

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'

    # setup
    business = create_business(identifier)
    test_filing = create_filing(payment_id, AR_FILING, business.id)

    # TEST
    with pytest.raises(Exception):
        process_filing(test_filing, flask_app=None)


def test_process_filing(app, session):
    """Assert that an AR filling can be applied to the model correctly."""
    from entity_filer.worker import process_filing
    from entity_filer.worker import get_filing_by_payment_id
    from legal_api.models import Business

    # vars
    payment_id = str(random.SystemRandom().getrandbits(0x58))
    identifier = 'CP1234567'
    agm_date = datetime.date.fromisoformat(AR_FILING['filing']['annualReport'].get('annualGeneralMeetingDate'))

    # setup
    business = create_business(identifier)
    business_id = business.id
    test_filing = create_filing(payment_id, AR_FILING, business.id)

    # TEST
    process_filing(test_filing, app)

    # Get modified data
    filing = get_filing_by_payment_id(payment_id)
    business = Business.find_by_internal_id(business_id)

    # check it out
    assert filing.transaction_id
    assert filing.business_id == business_id
    assert datetime.datetime.date(business.last_agm_date) == agm_date
    assert business.last_ar_date.replace(tzinfo=None) == EPOCH_DATETIME
