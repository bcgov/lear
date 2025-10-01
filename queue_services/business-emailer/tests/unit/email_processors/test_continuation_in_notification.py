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
from business_model.models import Filing

from business_emailer.email_processors import continuation_in_notification
from tests.unit import prep_continuation_in_filing


@pytest.mark.parametrize('status, subject, content', [
    (Filing.Status.APPROVED.value, 'Authorization Approved', 'Results of your Continuation Authorization'),
    (Filing.Status.AWAITING_REVIEW.value, 'Authorization Documents Received', 'We have received your Continuation Authorization documents'),
    (Filing.Status.CHANGE_REQUESTED.value, 'Changes Needed to Authorization', 'Make changes to your Continuation Authorization'),
    (Filing.Status.COMPLETED.value, 'Successful Continuation into B.C.', 'Your business has successfully continued into B.C.'),
    (Filing.Status.PAID.value, 'Continuation Application Received', 'Receipt'),
    (Filing.Status.REJECTED.value, 'Authorization Rejected', 'rejected'),
    ('RESUBMITTED', 'Authorization Updates Received', 'your updated'),
])
def test_continuation_in_notification(app, session, mocker, status, subject, content):
    """Assert Continuation notification is created."""
    # setup filing + business for email
    filing = prep_continuation_in_filing(session, 'C1234567', '1', status)
    token = 'token'

    # test processor
    mocker.patch(
        'business_emailer.email_processors.continuation_in_notification.get_entity_dashboard_url',
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
        assert email['content']['subject'] == subject
        assert content in email['content']['body']

        if status == Filing.Status.PAID.value:
            assert 'comp_party@email.com' in email['recipients']
