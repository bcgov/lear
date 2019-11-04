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


def create_filing_msg(identifier):
    """Create the filing payload."""
    filing_msg = {'filing': {'id': identifier}}
    return filing_msg


def get_filing_id_from_msg(msg: nats.aio.client.Msg):
    """Return the identifier of the filing in the NATS msg."""
    try:
        token = json.loads(msg.data.decode('utf-8'))
        return token['filing'].get('id')
    except (AttributeError, NameError, json.decoder.JSONDecodeError):
        return None


def create_payment_msg(identifier, status):
    """Create a payment payload for the paymentToken."""
    payment_msg = {'paymentToken': {'id': identifier, 'statusCode': status}}
    return payment_msg


def get_payment_id_from_msg(msg: nats.aio.client.Msg):
    """Extract the payment if from the NATS message."""
    try:
        token = json.loads(msg.data.decode('utf-8'))
        return token['paymentToken'].get('id')
    except (AttributeError, NameError, json.decoder.JSONDecodeError):
        return None
