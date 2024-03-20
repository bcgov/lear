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

from entity_emailer.email_processors import amalgamation_notification
from tests.unit import prep_amalgamation_filing


@pytest.mark.parametrize("status", [(Filing.Status.PAID.value), (Filing.Status.COMPLETED.value)])
def test_amalgamation_notification(app, session, status):
    """Assert Amalgamation notification is created."""
    # setup filing + business for email
    legal_name = "test business"
    filing = prep_amalgamation_filing(session, "BC1234567", "1", status, legal_name)
    token = "token"
    # test processor
    with patch.object(amalgamation_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = amalgamation_notification.process(
            {"filingId": filing.id, "type": "amalgamationApplication", "option": status}, token
        )

        assert "test@test.com" in email["recipients"]
        if status == Filing.Status.PAID.value:
            assert email["content"]["subject"] == legal_name + " - Amalgamation"
            assert "comp_party@email.com" in email["recipients"]
        else:
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "BC1234567"
            assert email["content"]["subject"] == legal_name + " - Confirmation of Amalgamation"

        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][3] == filing
