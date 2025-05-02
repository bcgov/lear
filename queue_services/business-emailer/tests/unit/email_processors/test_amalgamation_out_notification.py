# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests for the Amalgamation Out email processor."""
from unittest.mock import patch

import pytest
from business_model.models import Business

from business_emailer.email_processors import amalgamation_out_notification
from tests.unit import prep_amalgamation_out_filing


@pytest.mark.parametrize('status,legal_type,submitter_role', [
    ('COMPLETED', Business.LegalTypes.COMP.value, None),
    ('COMPLETED', Business.LegalTypes.BCOMP.value, None),
    ('COMPLETED', Business.LegalTypes.BC_CCC.value, None),
    ('COMPLETED', Business.LegalTypes.BC_ULC_COMPANY.value, None),
    ('COMPLETED', Business.LegalTypes.COMP.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.BCOMP.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.BC_CCC.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.BC_ULC_COMPANY.value, 'staff')
])
def test_amalgamation_out_notification(app, session, status, legal_type, submitter_role):
    """Assert that the amalgamation_out email processor for corps works as expected."""
    # setup filing + business for email
    legal_name = 'test business'
    filing = prep_amalgamation_out_filing(session, 'BC1234567', '1', legal_type, legal_name, submitter_role)
    token = 'token'
    # test processor
    with patch.object(amalgamation_out_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(amalgamation_out_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = amalgamation_out_notification.process(
                {'filingId': filing.id, 'type': 'amalgamationOut', 'option': status}, token)
            assert email['content']['subject'] == \
                legal_name + ' - Amalgamation Out'

            if submitter_role:
                assert f'{submitter_role}@email.com' in email['recipients']
            assert 'recipient@email.com' in email['recipients']
            assert email['content']['body']
            assert email['content']['attachments'] == []
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1]['identifier'] == 'BC1234567'
            assert mock_get_pdfs.call_args[0][1]['legalName'] == legal_name
            assert mock_get_pdfs.call_args[0][1]['legalType'] == legal_type
            assert mock_get_pdfs.call_args[0][2] == filing
