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
"""Test Suite to ensure message tracking is working as expected."""
from unittest.mock import patch

import pytest
from entity_queue_common.service_utils import EmailException, QueueException  # noqa: I001
from sqlalchemy.exc import OperationalError

from entity_emailer import worker
from tracker.models import MessageProcessing

from . import create_mock_message  # noqa: I003


@pytest.mark.parametrize(
    ['expected_msg_id', 'message_payload'],
    [
        ('16fd2706-8baf-433b-82eb-8c7fada847aa',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': 'nr_pay',
             'id': '16fd2706-8baf-433b-82eb-8c7fada847aa',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': '781020202',
             'data': {
                 'header': {'nrNum': '781020202'},
                 'paymentToken': '234234234324asjdkfhjsdhf23949239423',
                 'statusCode': 'PAID'
             }
         }),
        ('f36e3af7-90c3-4859-a6f6-2feefbdc1e37',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': '/requests/NR 1234567',
             'id': 'f36e3af7-90c3-4859-a6f6-2feefbdc1e37',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': 'NR 1234567',
             'data': {
                 'request': {
                     'nrNum': 'NR 1234567',
                     'option': 'before-expiry'
                 }
             }
         }),
        ('286ef5d3-600a-4b77-a27a-3bcaf8a16413',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': '/requests/NR 1234567',
             'id': '286ef5d3-600a-4b77-a27a-3bcaf8a16413',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': 'NR 1234567',
             'data': {
                 'request': {
                     'nrNum': 'NR 1234567',
                     'option': 'expired'
                 }
             }
         }),
        ('7a53d2ee-110c-4df5-85c0-6b0315eb5764',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': '/requests/NR 1234567',
             'id': '7a53d2ee-110c-4df5-85c0-6b0315eb5764',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': 'NR 1234567',
             'data': {
                 'request': {
                     'nrNum': 'NR 1234567',
                     'option': 'renewal'
                 }
             }
         }),
        ('8693f767-642c-4cea-acba-6af6526f2458',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': '/requests/NR 1234567',
             'id': '8693f767-642c-4cea-acba-6af6526f2458',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': 'NR 1234567',
             'data': {
                 'request': {
                     'nrNum': 'NR 1234567',
                     'option': 'upgrade'
                 }
             }
         }),
        ('cae39db6-cf40-4fd3-99c3-63b14ef8ccbd',
         {
             'specversion': '1.x-wip',
             'type': 'bc.registry.names.request',
             'source': '/requests/NR 1234567',
             'id': 'cae39db6-cf40-4fd3-99c3-63b14ef8ccbd',
             'time': '',
             'datacontenttype': 'application/json',
             'identifier': 'NR 1234567',
             'data': {
                 'request': {
                     'nrNum': 'NR 1234567',
                     'option': 'refund',
                     'refundValue': '123.45'
                 }
             }
         }),
        ('f36e3af7-90c3-4859-a6f6-2feefbdc1e30',
         {
            'specversion': '1.x-wip',
            'type': 'bc.registry.dissolution',
            'source': 'furnishingsJob',
            'id': 'f36e3af7-90c3-4859-a6f6-2feefbdc1e30',
            'time': '',
            'datacontenttype': 'application/json',
            'identifier': 'BC123223',
            'data': {
                'furnishing': {
                    'type': 'INVOLUNTARY_DISSOLUTION',
                    'furnishingId': 1,
                    'furnishingName': 'DISSOLUTION_COMMENCEMENT_NO_AR'
                }
            }
         }),
        ('f36e3af7-90c3-4859-a6f6-2feefbdc1e30',
         {
            'specversion': '1.x-wip',
            'type': 'bc.registry.dissolution',
            'source': 'furnishingsJob',
            'id': 'f36e3af7-90c3-4859-a6f6-2feefbdc1e30',
            'time': '',
            'datacontenttype': 'application/json',
            'identifier': 'BC123223',
            'data': {
                'furnishing': {
                    'type': 'INVOLUNTARY_DISSOLUTION',
                    'furnishingId': 1,
                    'furnishingName': 'DISSOLUTION_COMMENCEMENT_NO_TR'
                }
            }
         }),
        ('bc.registry.affiliation_1',
         {
             'type': 'bc.registry.affiliation',
             'identifier': 'BC1234567',
             'data': {
                 'filing': {
                     'header': {
                         'filingId': 1,
                     },
                 }
             }
         }),
        ('bc.registry.bnmove_993777399BC0001',
         {
             'type': 'bc.registry.bnmove',
             'identifier': 'FM1234567',
             'data': {
                 'oldBn': '993775204BC0001',
                 'newBn': '993777399BC0001'
             }
         }),
        ('businessNumber_BC1234567',
         {'email': {
             'type': 'businessNumber',
             'option': None,
             'filingId': '',
             'identifier': 'BC1234567'
         }
         }),
        ('incorporationApplication_mras_8238434',
         {
             'email': {
                 'type': 'incorporationApplication',
                 'option': 'mras',
                 'filingId': '8238434'
             }
         }),
        ('annualReport_COMPLETED_2323432432',
         {
             'email': {
                 'type': 'annualReport',
                 'option': 'COMPLETED',
                 'filingId': '2323432432'
             }
         }),
        ('annualReport_reminder_2021_33339999',
         {
             'email': {
                 'type': 'annualReport',
                 'option': 'reminder',
                 'businessId': '33339999',
                 'arFee': '100',
                 'arYear': 2021
             }
         }),
        ('agmLocationChange_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'agmLocationChange',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('agmExtension_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'agmExtension',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('alteration_PAID_1112223333',
         {
             'email': {
                 'type': 'alteration',
                 'option': 'PAID',
                 'filingId': '1112223333'
             }
         }),
        ('alteration_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'alteration',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('dissolution_PAID_1112223333',
         {
             'email': {
                 'type': 'dissolution',
                 'option': 'PAID',
                 'filingId': '1112223333'
             }
         }),
        ('dissolution_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'dissolution',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('registration_PAID_1112223333',
         {
             'email': {
                 'type': 'registration',
                 'option': 'PAID',
                 'filingId': '1112223333'
             }
         }),
        ('registration_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'registration',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('changeOfRegistration_PAID_1112223333',
         {
             'email': {
                 'type': 'changeOfRegistration',
                 'option': 'PAID',
                 'filingId': '1112223333'
             }
         }),
        ('changeOfRegistration_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'changeOfRegistration',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('consentAmalgamationOut_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'consentAmalgamationOut',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('consentContinuationOut_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'consentContinuationOut',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('continuationOut_COMPLETED_1112223333',
         {
             'email': {
                 'type': 'continuationOut',
                 'option': 'COMPLETED',
                 'filingId': '1112223333'
             }
         }),
        ('specialResolution_COMPLETED_111222333',
         {
             'email': {
                 'type': 'specialResolution',
                 'option': 'COMPLETED',
                 'filingId': '111222333'
             }
         }),
        ('specialResolution_PAID_111222333',
         {
             'email': {
                 'type': 'specialResolution',
                 'option': 'PAID',
                 'filingId': '111222333'
             }
         }),
        ('correction_PAID_111222334',
         {
             'email': {
                 'type': 'correction',
                 'option': 'PAID',
                 'filingId': '111222334'
             }
         }),
        ('correction_COMPLETED_111222335',
         {
             'email': {
                 'type': 'correction',
                 'option': 'COMPLETED',
                 'filingId': '111222335'
             }
         }),
        ('amalgamationApplication_PAID_111222334',
         {
             'email': {
                 'type': 'amalgamationApplication',
                 'option': 'PAID',
                 'filingId': '111222334'
             }
         }),
        ('amalgamationApplication_COMPLETED_111222335',
         {
             'email': {
                 'type': 'amalgamationApplication',
                 'option': 'COMPLETED',
                 'filingId': '111222335'
             }
         }),
        ('noticeOfWithdrawal_COMPLETED_111222335',
         {
             'email': {
                 'type': 'noticeOfWithdrawal',
                 'option': 'COMPLETED',
                 'filingId': '111222335'
             }
         })
    ]
)
@pytest.mark.asyncio
async def test_should_successfully_process_valid_messages_for_all_supported_message_types(
        tracker_app,
        tracker_db,
        session,
        expected_msg_id,
        message_payload):
    """Assert that all valid messages for all supported message types are processed successfully."""
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to return true to simulate successful email processing
    with patch.object(worker, 'process_email', return_value=True):
        await worker.cb_subscription_handler(mock_msg)
        result = MessageProcessing.find_message_by_message_id(message_id=expected_msg_id)
        assert result
        assert result.message_id == expected_msg_id
        assert result.status == 'COMPLETE'


@pytest.mark.asyncio
async def test_should_not_reprocess_completed_message(tracker_app, tracker_db, session):
    """Assert that processed(status=COMPLETE) messages are not re-processed."""
    message_id = '16fd2111-8baf-433b-82eb-8c7fada847aa'
    message_payload = {
        'specversion': '1.x-wip',
        'type': 'bc.registry.names.request',
        'source': 'nr_pay',
        'id': message_id,
        'time': '',
        'datacontenttype': 'application/json',
        'identifier': '781020202',
        'data': {
            'header': {'nrNum': '781020202'},
            'paymentToken': '234234234324asjdkfhjsdhf23949239423',
            'statusCode': 'PAID'
        }
    }
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to return true to simulate successful email processing
    with patch.object(worker, 'process_email', return_value=True):
        await worker.cb_subscription_handler(mock_msg)
        result_1st_time = MessageProcessing.find_message_by_message_id(message_id=message_id)
        assert result_1st_time.message_seen_count == 1

        await worker.cb_subscription_handler(mock_msg)
        result_2nd_time = MessageProcessing.find_message_by_message_id(message_id=message_id)
        assert result_2nd_time.message_seen_count == 1
        assert result_2nd_time.last_update == result_1st_time.last_update
        assert result_2nd_time.status == 'COMPLETE'


@pytest.mark.asyncio
async def test_should_mark_message_as_failed_on_queue_exception(tracker_app, tracker_db, session):
    """Assert that message is marked as failed on queue exception."""
    message_id = '16fd2111-8baf-433b-82eb-8c7fada84bbb'
    message_payload = {
        'specversion': '1.x-wip',
        'type': 'bc.registry.names.request',
        'source': 'nr_pay',
        'id': message_id,
        'time': '',
        'datacontenttype': 'application/json',
        'identifier': '781020202',
        'data': {
            'header': {'nrNum': '781020202'},
            'paymentToken': '234234234324asjdkfhjsdhf23949239423',
            'statusCode': 'PAID'
        }
    }
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to throw queue exception to simulate failed scenario
    with patch.object(worker, 'process_email', side_effect=QueueException('Queue Error.')):
        await worker.cb_subscription_handler(mock_msg)
        result = MessageProcessing.find_message_by_message_id(message_id=message_id)
        assert result
        assert result.status == 'FAILED'
        assert result.message_seen_count == 1
        assert result.last_error == 'QueueException, Exception - Queue Error.'


@pytest.mark.asyncio
async def test_should_mark_message_as_failed_on_email_exception(tracker_app, tracker_db, session):
    """Assert that message is marked as failed on email exception."""
    message_id = '16fd2111-8baf-433b-82eb-8c7fada84ccc'
    message_payload = {
        'specversion': '1.x-wip',
        'type': 'bc.registry.names.request',
        'source': 'nr_pay',
        'id': message_id,
        'time': '',
        'datacontenttype': 'application/json',
        'identifier': '781020202',
        'data': {
            'header': {'nrNum': '781020202'},
            'paymentToken': '234234234324asjdkfhjsdhf23949239423',
            'statusCode': 'PAID'
        }
    }
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to throw EmailException to simulate failed scenario
    with patch.object(worker, 'process_email', side_effect=EmailException('Unsuccessful response when sending email.')):
        # check that EmailException raised
        with pytest.raises(EmailException):
            await worker.cb_subscription_handler(mock_msg)

        result = MessageProcessing.find_message_by_message_id(message_id=message_id)
        assert result
        assert result.status == 'FAILED'
        assert result.message_seen_count == 1
        assert result.last_error == 'EmailException - Unsuccessful response when sending email.'


@pytest.mark.asyncio
async def test_should_process_previously_failed_message_successfully(tracker_app, tracker_db, session):
    """Assert that message that failed processing previously can be processed successfully."""
    message_id = '16fd2111-8baf-433b-82eb-8c7fada84ddd'
    message_payload = {
        'specversion': '1.x-wip',
        'type': 'bc.registry.names.request',
        'source': 'nr_pay',
        'id': message_id,
        'time': '',
        'datacontenttype': 'application/json',
        'identifier': '781020202',
        'data': {
            'header': {'nrNum': '781020202'},
            'paymentToken': '234234234324asjdkfhjsdhf23949239423',
            'statusCode': 'PAID'
        }
    }
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to throw email exception to simulate failed scenario
    with patch.object(worker, 'process_email', side_effect=EmailException('Unsuccessful response when sending email.')):
        with pytest.raises(EmailException):
            await worker.cb_subscription_handler(mock_msg)

    # mock out process_email function to simulate success scenario
    with patch.object(worker, 'process_email', return_value=True):
        await worker.cb_subscription_handler(mock_msg)
        result = MessageProcessing.find_message_by_message_id(message_id=message_id)
        assert result
        assert result.status == 'COMPLETE'
        assert result.message_seen_count == 2
        assert result.last_error == 'EmailException - Unsuccessful response when sending email.'


@pytest.mark.asyncio
@pytest.mark.parametrize(['message_id', 'exception', 'args', 'expected_last_error'], [
    ('16fd2111-8baf-433b-82eb-8c7fada84eea', OperationalError, [None, None, None], 'OperationalError'),
    ('16fd2111-8baf-433b-82eb-8c7fada84eeb', EmailException,
     ['Unsucessful response when sending email.'], 'EmailException'),
    ('16fd2111-8baf-433b-82eb-8c7fada84eec', QueueException, ['Queue error.'], 'QueueException, Exception'),
    ('16fd2111-8baf-433b-82eb-8c7fada84eed', Exception, ['Other error.'], 'QueueException, Exception')
])
async def test_should_correctly_track_retries_for_failed_processing(tracker_app, tracker_db, session,
                                                                    message_id, exception, args, expected_last_error):
    """Assert that message processing retries are properly tracked."""
    message_payload = {
        'specversion': '1.x-wip',
        'type': 'bc.registry.names.request',
        'source': 'nr_pay',
        'id': message_id,
        'time': '',
        'datacontenttype': 'application/json',
        'identifier': '781020202',
        'data': {
            'header': {'nrNum': '781020202'},
            'paymentToken': '234234234324asjdkfhjsdhf23949239423',
            'statusCode': 'PAID'
        }
    }
    mock_msg = create_mock_message(message_payload)

    # mock out process_email function to throw exception to simulate failed scenario
    with patch.object(worker, 'process_email', side_effect=exception(*args)):
        for _ in range(6):
            if exception in [OperationalError, EmailException]:
                with pytest.raises(exception):
                    await worker.cb_subscription_handler(mock_msg)
            else:
                await worker.cb_subscription_handler(mock_msg)

    # mock out process_email function not to process since message reaches max retries
    with patch.object(worker, 'process_email', side_effect=exception(*args)):
        for _ in range(5):
            await worker.cb_subscription_handler(mock_msg)

    result = MessageProcessing.find_message_by_message_id(message_id=message_id)
    assert result
    assert result.status == 'FAILED'
    # check email retries not exceed the max retry limit
    assert result.message_seen_count == 6
    assert expected_last_error in result.last_error
