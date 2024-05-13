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
# import json
# import random

# import pytest

# # from tests.unit import create_business, create_director, create_filing  # noqa I001, E501;
# from tests.unit import create_business, create_filing  # noqa I001, E501;


# def test_extract_payment_token():
#     """Assert that the payment token can be extracted from the Queue delivered Msg."""
#     import stan.pb.protocol_pb2 as protocol
#     from stan.aio.client import Msg

#     from entity_pay.worker import extract_payment_token

#     # setup
#     token = {'paymentToken': {'id': 1234, 'statusCode': 'COMPLETED'}}
#     msg = Msg()
#     msg.proto = protocol.MsgProto
#     msg.proto.data = json.dumps(token).encode('utf-8')

#     # test and verify
#     assert extract_payment_token(msg) == token


# def test_get_filing_by_payment_id(app, session):
#     """Assert that a unique filling gets retrieved for a filing id."""
#     from entity_pay.worker import get_filing_by_payment_id

#     payment_id = str(random.SystemRandom().getrandbits(0x58))

#     create_filing(payment_id)

#     filing = get_filing_by_payment_id(int(payment_id))

#     assert filing
#     assert filing.payment_token == payment_id


# async def test_process_payment_missing_app(app, session):
#     """Assert that a filling will fail with no flask app supplied."""
#     from legal_api.models import Filing

#     from entity_pay.worker import process_payment

#     # vars
#     payment_id = str(random.SystemRandom().getrandbits(0x58))
#     identifier = 'CP1234567'

#     # setup
#     business = create_business(identifier)
#     create_filing(payment_id, None, business.id)
#     payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

#     # TEST
#     with pytest.raises(Exception):
#         await process_payment(payment_token, flask_app=None)


# async def test_process_empty_filing(app, session):
#     """Assert that an AR filling can be applied to the model correctly."""
#     from legal_api.models import Filing

#     from entity_pay.worker import get_filing_by_payment_id, process_payment

#     # vars
#     payment_id = str(random.SystemRandom().getrandbits(0x58))
#     identifier = 'CP1234567'

#     # setup
#     business = create_business(identifier)
#     business_id = business.id
#     create_filing(payment_id, None, business.id)
#     payment_token = {'paymentToken': {'id': payment_id, 'statusCode': Filing.Status.COMPLETED.value}}

#     # TEST
#     await process_payment(payment_token, app)

#     # Get modified data
#     filing = get_filing_by_payment_id(int(payment_id))

#     # check it out
#     assert filing.business_id == business_id
#     assert filing.status == Filing.Status.PAID.value


# async def test_process_payment_failed(app, session):
#     """Assert that an AR filling status is set to error if payment transaction failed."""
#     from legal_api.models import Business, Filing

#     from entity_pay.worker import get_filing_by_payment_id, process_payment

#     # vars
#     payment_id = str(random.SystemRandom().getrandbits(0x58))
#     identifier = 'CP1234567'

#     # setup
#     business = create_business(identifier)
#     business_id = business.id
#     create_filing(payment_id, None, business.id)
#     payment_token = {'paymentToken': {'id': payment_id,
#                                       'statusCode': 'TRANSACTION_FAILED'}}

#     # TEST
#     await process_payment(payment_token, app)

#     # Get modified data
#     filing = get_filing_by_payment_id(int(payment_id))
#     business = Business.find_by_internal_id(business_id)

#     # check it out
#     assert filing.business_id == business_id
#     assert filing.status == Filing.Status.PENDING.value
#     assert not business.last_agm_date
#     assert not business.last_ar_date


# @pytest.mark.parametrize('name,filing_id,corp_type_code,expected_result', [
#     ('success', '1', 'BEN', True),
#     ('success', '1', 'CP', True),
#     ('success', '1', 'SP', True),
#     ('success', '1', 'GP', True),
#     ('success', '1', 'BC', True),
#     ('success', '1', 'ULC', True),
#     ('success', '1', 'CC', True),
#     ('fail_invalid_corp_type', '1', None, False),
#     ('fail_invalid_corp_type', '1', 'CSO', False),
#     ('fail_no_payment_token', '1', 'BC', False),
# ])
# def test_is_processable_message(app, session, name, filing_id, corp_type_code, expected_result):
#     """Assert that the queue message is processable only when msg meets required criteria."""
#     from entity_pay.worker import is_processable_message

#     # setup
#     if name == 'fail_no_payment_token':
#         msg = {'paymentToken': None}
#     else:
#         msg = {'paymentToken': {'id': 1234,
#                                 'statusCode': 'COMPLETED',
#                                 'corpTypeCode': corp_type_code}}

#     # test and verify
#     assert is_processable_message(msg) == expected_result
