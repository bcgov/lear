# Copyright © 2022 Province of British Columbia
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
"""The Unit Tests for the Change of Registration email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import Business

from entity_emailer.email_processors import change_of_registration_notification
from tests.unit import prep_change_of_registration_filing


@pytest.mark.parametrize('status,legal_type', [
    ('PAID', Business.LegalTypes.SOLE_PROP.value),
    ('COMPLETED', Business.LegalTypes.SOLE_PROP.value),
    ('PAID', Business.LegalTypes.PARTNERSHIP.value),
    ('COMPLETED', Business.LegalTypes.PARTNERSHIP.value),
])
def test_change_of_registration_notification(app, session, status, legal_type):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = 'test business'
    filing = prep_change_of_registration_filing(session, 'FM1234567', '1', legal_type, legal_name, 'staff')
    token = 'token'
    # test processor
    with patch.object(change_of_registration_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = change_of_registration_notification.process(
            {'filingId': filing.id, 'type': 'changeOfRegistration', 'option': status}, token)
        if status == 'PAID':
            assert email['content']['subject'] == legal_name + ' - Confirmation of Filing from the Business Registry'
        else:
            assert email['content']['subject'] == \
                legal_name + ' - Change of Registration Documents from the Business Registry'

        if status == 'COMPLETED':
            assert 'no_one@never.get' in email['recipients']
            if legal_type == Business.LegalTypes.PARTNERSHIP.value:
                assert 'party@email.com' in email['recipients']

        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == 'COMPLETED':
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'FM1234567'
        assert mock_get_pdfs.call_args[0][3] == filing
