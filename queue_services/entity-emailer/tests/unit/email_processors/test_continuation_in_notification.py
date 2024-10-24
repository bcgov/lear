# Copyright © 2024 Province of British Columbia
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
"""The Unit Tests for the Amalgamation email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import Filing

from entity_emailer.email_processors import continuation_in_notification
from tests.unit import prep_continuation_in_filing


@pytest.mark.parametrize('status', [
    (Filing.Status.APPROVED.value),
    (Filing.Status.AWAITING_REVIEW.value),
    (Filing.Status.CHANGE_REQUESTED.value),
    (Filing.Status.COMPLETED.value),
    (Filing.Status.PAID.value),
    (Filing.Status.REJECTED.value),
    ('RESUBMITTED'),
])
def test_continuation_in_notification(app, session, mocker, status):
    """Assert Continuation notification is created."""
    # setup filing + business for email
    filing = prep_continuation_in_filing(session, 'C1234567', '1', status)
    token = 'token'

    # test processor
    mocker.patch(
        'entity_emailer.email_processors.continuation_in_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(continuation_in_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = continuation_in_notification.process(
            {'filingId': filing.id, 'type': 'continuationIn', 'option': status}, token)

        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][3] == filing

        # spot check email content based on status
        if status == Filing.Status.APPROVED.value:
            assert email['content']['subject'] == 'Authorization Approved'
            assert 'Results of your Continuation Authorization' in email['content']['body']
        
        elif status == Filing.Status.AWAITING_REVIEW.value:
            assert email['content']['subject'] == 'Authorization Documents Received'
            assert 'We have received your Continuation Authorization documents' in email['content']['body']

        elif status == Filing.Status.CHANGE_REQUESTED.value:
            assert email['content']['subject'] == 'Changes Needed to Authorization'
            assert 'Make changes to your Continuation Authorization' in email['content']['body']

        elif status == Filing.Status.COMPLETED.value:
            assert email['content']['subject'] == 'Successful Continuation into B.C.'
            assert 'Your business has successfully continued into B.C.' in email['content']['body']
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'C1234567'

        elif status == Filing.Status.PAID.value:
            assert email['content']['subject'] == \
                'HAULER MEDIA INC. - Continuation Application Received'
            assert 'Receipt' in email['content']['body']
            assert 'comp_party@email.com' in email['recipients']

        elif status == Filing.Status.REJECTED.value:
            assert email['content']['subject'] == 'Authorization Rejected'
            assert 'rejected' in email['content']['body']

        elif status == 'RESUBMITTED':
            assert email['content']['subject'] == 'Authorization Updates Received'
            assert 'your updated' in email['content']['body']
