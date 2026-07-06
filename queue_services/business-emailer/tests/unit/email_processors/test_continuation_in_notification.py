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
"""The Unit Tests for the Continuation In review step email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Filing

from business_emailer.email_processors import continuation_in_notification
from tests.unit import CONTACT_POINT, prep_bootstrap_filing


@pytest.mark.parametrize('status, subject, content', [
    (Filing.Status.APPROVED.value, 'Authorization Approved', 'Results of your Continuation Authorization'),
    (Filing.Status.AWAITING_REVIEW.value, 'Authorization Documents Received', 'We have received your Continuation Authorization documents'),
    (Filing.Status.CHANGE_REQUESTED.value, 'Changes Needed to Authorization', 'Make changes to your Continuation Authorization'),
    (Filing.Status.REJECTED.value, 'Authorization Rejected', 'rejected'),
    ('RESUBMITTED', 'Authorization Updates Received', 'your updated'),
])
def test_continuation_in_notification(app, session, mocker, status, subject, content):
    """Assert Continuation review notification is created."""
    # setup filing + business for email
    filing = prep_bootstrap_filing(session, 'continuationIn', 'C1234567', 'BC', status)
    token = 'token'

    # test processor
    with patch.object(continuation_in_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = continuation_in_notification.process(
            {'filingId': filing.id, 'type': 'continuationIn', 'option': status}, token)

        assert CONTACT_POINT in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][3] == filing

        # spot check email content based on status
        assert email['content']['subject'] == subject
        assert content in email['content']['body']


def test_continuation_in_attachments_resubmitted(session, mocker, config):
    """Assert RESUBMITTED path attaches only the Continuation Application (Resubmitted)."""
    filing = prep_bootstrap_filing(session, 'continuationIn', 'C1234567', 'BC', 'RESUBMITTED')
    identifier = filing.temp_reg
    token = 'token'
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/continuationIn?regenerate=True',
            content=b'pdf_content_1',
            status_code=200,
        )
        output = continuation_in_notification.process(
            {'filingId': filing.id, 'type': 'continuationIn', 'option': 'RESUBMITTED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 1
    assert attachments[0]['fileName'] == 'Continuation Application - Resubmitted.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
