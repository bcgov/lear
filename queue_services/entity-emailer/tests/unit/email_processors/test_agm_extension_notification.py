# Copyright © 2023 Province of British Columbia
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
"""The Unit Tests for AGM extension email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import LegalEntity

from entity_emailer.email_processors import agm_extension_notification
from tests.unit import prep_agm_extension_filing


@pytest.mark.parametrize(
    "status,legal_name,is_numbered",
    [
        ("COMPLETED", "test business", False),
        ("COMPLETED", "BC1234567", True),
    ],
)
def test_agm_extension_notification(app, session, status, legal_name, is_numbered):
    """Assert that the agm extension email processor works as expected."""
    # setup filing + business for email
    filing = prep_agm_extension_filing("BC1234567", "1", LegalEntity.EntityTypes.COMP.value, legal_name)
    token = "token"
    # test processor
    with patch.object(agm_extension_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        with patch.object(agm_extension_notification, "get_recipient_from_auth", return_value="recipient@email.com"):
            email = agm_extension_notification.process(
                {"filingId": filing.id, "type": "agmExtension", "option": status}, token
            )

            if is_numbered:
                assert (
                    email["content"]["subject"]
                    == "Numbered Company - AGM Extension Documents from the Business Registry"
                )
            else:
                assert (
                    email["content"]["subject"] == legal_name + " - AGM Extension Documents from the Business Registry"
                )

            assert "recipient@email.com" in email["recipients"]
            assert email["content"]["body"]
            assert email["content"]["attachments"] == []
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1]["identifier"] == "BC1234567"
            assert mock_get_pdfs.call_args[0][1]["legalName"] == legal_name
            assert mock_get_pdfs.call_args[0][1]["legalType"] == LegalEntity.EntityTypes.COMP.value
            assert mock_get_pdfs.call_args[0][2] == filing
