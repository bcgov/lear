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
"""The Unit Tests for the annual report reminder email processor."""
from unittest.mock import patch

import pytest

from business_emailer.email_processors import ar_reminder_notification
from business_model.models import Business
from tests.unit import prep_incorp_filing


@pytest.mark.parametrize('test_name, legal_type, tax_id, expected_business_number', [
    ('BC_NO_BN', 'BC', None, None),
    ('BC_BN9_HIDDEN', 'BC', '123456789', None),
    ('BEN_BN15', 'BEN', '85684951BC0001', '85684951 BC0001'),
])
def test_ar_reminder_notification(app, session, test_name, legal_type, tax_id, expected_business_number):
    """Assert that the ar reminder notification can be processed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', 'COMPLETED')
    business = Business.find_by_internal_id(filing.business_id)
    business.legal_type = legal_type
    business.legal_name = 'test business'
    business.tax_id = tax_id
    token = 'token'
    # test processor
    with patch.object(ar_reminder_notification, 'get_recipient_from_auth', return_value='test@test.com') \
            as mock_get_recipient_from_auth:
        email = ar_reminder_notification.process(
            {
              'businessId': filing.business_id,
              'type': 'annualReport', 'option': 'reminder',
              'arFee': '43.39', 'arYear': 2021
            }, token)
        assert email['content']['subject'] == 'test business - Annual Report Reminder'

        assert 'test@test.com' in email['recipients']
        assert email['content']['attachments'] == []
        assert mock_get_recipient_from_auth.call_args[0][0] == 'BC1234567'
        assert mock_get_recipient_from_auth.call_args[0][1] == token

        body = email['content']['body']
        assert body
        assert '# You can now file your 2021 annual report with the BC Business Registry' in body
        assert '[Section 51 of the *Business Corporations Act*]' \
               '(https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_02#section51)' in body
        assert '**Business Name:** test business' in body
        assert '**Incorporation Number:** BC1234567' in body
        if expected_business_number:
            assert f'**Business Number:** {expected_business_number}' in body
        else:
            assert '**Business Number:**' not in body
        assert '## Next Steps' in body
        assert 'You have 60 days to file your annual report' in body
        assert f'[BC Business Registry account]({app.config.get("DASHBOARD_URL")}BC1234567)' in body
        assert 'The filing fee is $43.39 + $1.50 service fee.' in body
        assert '## Additional Resources' in body
        assert 'Service BC does not provide legal or financial advice' in body
        assert 'contact an accountant, lawyer or service provider of your choice' in body
        assert 'Dye & Durham' not in body
        if legal_type in ['BEN', 'CBEN']:
            assert 'annual Benefit Report' in body
        else:
            assert 'Benefit Report' not in body
        assert '**Business Registry**' in body
        assert '.md]]' not in body
