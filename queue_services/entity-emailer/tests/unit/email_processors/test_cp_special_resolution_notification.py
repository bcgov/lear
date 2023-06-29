# Copyright © 2021 Province of British Columbia
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
"""The Unit Tests for the Special Resolution email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import Business

from entity_emailer.email_processors import special_resolution_notification
from tests.unit import prep_cp_special_resolution_filing


@pytest.mark.parametrize('status', [
    ('PAID'),
    ('COMPLETED')
])
def test_cp_special_resolution_notification(app, session, status):
    """Assert that the special resolution email processor works as expected."""
    # setup filing + business for email
    legal_name = 'test business'
    legal_type = Business.LegalTypes.COOP.value
    filing = prep_cp_special_resolution_filing(session, 'CP1234567', '1', legal_type, legal_name)
    token = 'token'
    # test processor
    with patch.object(special_resolution_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(special_resolution_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = special_resolution_notification.process(
                {'filingId': filing.id, 'type': 'specialResolution', 'option': status}, token)
            if status == 'PAID':
                assert email['content']['subject'] == legal_name + \
                    ' - Confirmation of Special Resolution from the Business Registry'
            else:
                assert email['content']['subject'] == \
                    legal_name + ' - Special Resolution Documents from the Business Registry'

            assert 'recipient@email.com' in email['recipients']
            assert email['content']['body']
            assert email['content']['attachments'] == []
            assert mock_get_pdfs.call_args[0][0] == status
            assert mock_get_pdfs.call_args[0][1] == token
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'CP1234567'
            assert mock_get_pdfs.call_args[0][2]['legalName'] == legal_name
            assert mock_get_pdfs.call_args[0][2]['legalType'] == legal_type
            assert mock_get_pdfs.call_args[0][3] == filing
