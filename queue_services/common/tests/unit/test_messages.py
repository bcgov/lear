# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""All of the message templates used across the various services."""
import json

import nats
import stan.pb.protocol_pb2 as protocol
from stan.aio.client import Msg

from entity_queue_common import messages


def test_create_filing_msg():
    """Assert that the payment token can be created."""
    identifier = 'test_id'
    filing_msg = messages.create_filing_msg(identifier)
    assert filing_msg == {'filing': {'id': identifier}}


def test_get_filing_id_from_msg():
    """Assert the identifier of the filing in the NATS msg."""
    # setup
    identifier = 'test_id'
    token = {'filing': {'id': identifier}}
    msg = Msg()
    msg.proto = protocol.MsgProto
    msg.proto.data = json.dumps(token).encode('utf-8')

    assert identifier == messages.get_filing_id_from_msg(msg)
    assert not messages.get_filing_id_from_msg(None)


def test_create_payment_msg():
    """Assert a payment message can be created."""
    # setup
    identifier = 'test_id'
    status = 'TEST_STATUS'

    return messages.create_payment_msg(identifier, status) == {'paymentToken': {'id': identifier, 'statusCode': status}}


def test_get_payment_id_from_msg():
    """Assert that an id can be extracted from the payment message."""
    # setup
    identifier = 'test_id'
    status = 'TEST_STATUS'
    token = {'paymentToken': {'id': identifier, 'statusCode': status}}
    msg = Msg()
    msg.proto = protocol.MsgProto
    msg.proto.data = json.dumps(token).encode('utf-8')

    assert identifier == messages.get_payment_id_from_msg(msg)
    assert not messages.get_payment_id_from_msg(None)
