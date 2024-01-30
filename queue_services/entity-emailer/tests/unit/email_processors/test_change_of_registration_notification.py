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
from legal_api.models import LegalEntity

from entity_emailer.email_processors import change_of_registration_notification
from tests.unit import prep_change_of_registration_filing


@pytest.mark.parametrize(
    "status,legal_type,submitter_role",
    [
        ("PAID", LegalEntity.EntityTypes.SOLE_PROP.value, None),
        ("COMPLETED", LegalEntity.EntityTypes.SOLE_PROP.value, None),
        ("PAID", LegalEntity.EntityTypes.PARTNERSHIP.value, None),
        ("COMPLETED", LegalEntity.EntityTypes.PARTNERSHIP.value, None),
        ("PAID", LegalEntity.EntityTypes.SOLE_PROP.value, "staff"),
        ("COMPLETED", LegalEntity.EntityTypes.SOLE_PROP.value, "staff"),
        ("PAID", LegalEntity.EntityTypes.PARTNERSHIP.value, "staff"),
        ("COMPLETED", LegalEntity.EntityTypes.PARTNERSHIP.value, "staff"),
    ],
)
def test_change_of_registration_notification(app, session, mocker, status, legal_type, submitter_role):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = "test business"
    filing = prep_change_of_registration_filing(session, "FM1234567", "1", legal_type, legal_name, submitter_role)
    token = "token"
    # test processor
    mocker.patch(
        "entity_emailer.email_processors.change_of_registration_notification.get_user_email_from_auth",
        return_value="user@email.com",
    )
    with patch.object(change_of_registration_notification, "_get_pdfs", return_value=[]) as mock_get_pdfs:
        email = change_of_registration_notification.process(
            {"filingId": filing.id, "type": "changeOfRegistration", "option": status}, token
        )
        if status == "PAID":
            assert email["content"]["subject"] == legal_name + " - Confirmation of Filing from the Business Registry"
        else:
            assert (
                email["content"]["subject"]
                == legal_name + " - Change of Registration Documents from the Business Registry"
            )

        if submitter_role:
            assert f"{submitter_role}@email.com" in email["recipients"]
        else:
            assert "user@email.com" in email["recipients"]

        if status == "COMPLETED":
            assert "no_one@never.get" in email["recipients"]
            if legal_type == LegalEntity.EntityTypes.PARTNERSHIP.value:
                assert "party@email.com" in email["recipients"]

        assert email["content"]["body"]
        assert email["content"]["attachments"] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == "COMPLETED":
            assert mock_get_pdfs.call_args[0][2]["identifier"] == "FM1234567"
        assert mock_get_pdfs.call_args[0][3] == filing
