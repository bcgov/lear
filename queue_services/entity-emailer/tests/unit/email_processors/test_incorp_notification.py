# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation email processor."""
from unittest.mock import patch

import pytest

from entity_emailer.email_processors import incorp_notification
from tests.unit import email_prepped_filing


@pytest.mark.parametrize('option', [
    ('filed'),
    ('registered'),
])
def test_incorp_notification(app, session, option):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = email_prepped_filing(session, 'BC1234567', '1', option)
    token = 'token'
    # test processor
    with patch.object(incorp_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = incorp_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': option}, token)
        if option == 'filed':
            assert 'comp_party@email.com' in email['recipients']
            assert email['content']['subject'] == 'Confirmation of Filing from the Business Registry'
        else:
            assert email['content']['subject'] == 'Incorporation Documents from the Business Registry'

        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == option
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][2] == {'identifier': 'BC1234567'}
        assert mock_get_pdfs.call_args[0][3] == filing
