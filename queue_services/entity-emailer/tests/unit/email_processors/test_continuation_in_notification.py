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


@pytest.mark.parametrize(['status', 'subject'], [
    (Filing.Status.APPROVED.value, ''),
    (Filing.Status.CHANGE_REQUESTED.value, ''),
    (Filing.Status.COMPLETED.value, ''),
    (Filing.Status.PAID.value, ''),
    (Filing.Status.REJECTED.value, ''),
    ('RESUBMITTED', ''),
])
def test_continuation_in_notification(app, session, mocker, status, subject):
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

        if status == Filing.Status.APPROVED.value:
            assert email['content']['subject'] == \
                'Results of your Filing from the Business Registry'

        elif status == Filing.Status.CHANGE_REQUESTED.value:
            assert email['content']['subject'] == \
                'Change Requested from the Business Registry'

        elif status == Filing.Status.COMPLETED.value:
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'C1234567'
            assert email['content']['subject'] == 'Continuation Documents from the Business Registry'

        elif status == Filing.Status.PAID.value:
            assert email['content']['subject'] == \
                'HAULER MEDIA INC. - Confirmation of Filing from the Business Registry'
            assert 'comp_party@email.com' in email['recipients']

        elif status == Filing.Status.REJECTED.value:
            assert email['content']['subject'] == \
                'Results of your Filing from the Business Registry'

        elif status == 'RESUBMITTED':
            assert email['content']['subject'] == \
                'Confirmation of Filing from the Business Registry'

        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][3] == filing

        # FUTURE: verify some html_out content
