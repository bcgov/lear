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

from legal_api.models import LegalEntity

from entity_emailer.email_processors import ar_reminder_notification
from tests.unit import prep_incorp_filing


def test_ar_reminder_notification(app, session):
    """Assert that the ar reminder notification can be processed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, "BC1234567", "1", "COMPLETED")
    business = LegalEntity.find_by_internal_id(filing.legal_entity_id)
    business.legal_type = "BC"
    business.legal_name = "test business"
    token = "token"
    flag_on = False
    # test processor
    with patch.object(
        ar_reminder_notification, "get_recipient_from_auth", return_value="test@test.com"
    ) as mock_get_recipient_from_auth:
        email = ar_reminder_notification.process(
            {
                "businessId": filing.legal_entity_id,
                "type": "annualReport",
                "option": "reminder",
                "arFee": "100",
                "arYear": 2021,
            },
            token,
            flag_on,
        )
        assert email["content"]["subject"] == "test business 2021 Annual Report Reminder"

        assert "test@test.com" in email["recipients"]
        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
        assert mock_get_recipient_from_auth.call_args[0][0] == "BC1234567"
        assert mock_get_recipient_from_auth.call_args[0][1] == token
