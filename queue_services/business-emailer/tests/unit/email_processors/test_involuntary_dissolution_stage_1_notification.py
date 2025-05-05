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
"""The Unit Tests for the involuntary_dissolution_stage_1_notification processor."""
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest
import requests
from simple_cloudevent import SimpleCloudEvent
from business_model.models import Furnishing

from business_emailer.email_processors import involuntary_dissolution_stage_1_notification
from tests.unit import create_business, create_furnishing  # noqa: I003


@pytest.mark.parametrize(
        'test_name, legal_type, furnishing_name', [
            ('TEST_BC_NO_AR', 'BC', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR),
            # next one is failing, needs more investigation why ??!?
            ('TEST_XPRO_NO_AR', 'A', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO),
            ('TEST_BC_NO_TR', 'BC', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR),
        ]
)
def test_involuntary_dissolution_stage_1_notification(app, session, test_name, legal_type, furnishing_name):
    """Assert that the test_involuntary_dissolution_stage_1_notification can be processed."""
    token = 'token'
    business_identifier = 'BC1234567'
    business = create_business(business_identifier, legal_type, 'Test Business')
    furnishing = create_furnishing(session, business=business, furnishing_name=furnishing_name)
    message_payload = {
        'furnishing': {
            'type': 'INVOLUNTARY_DISSOLUTION',
            'furnishingId': furnishing.id,
            'furnishingName': furnishing.furnishing_name
        }
    }

    mock_response = MagicMock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {}
    with patch.object(
        involuntary_dissolution_stage_1_notification, '_get_pdfs', return_value=[{'TEST': 'TEST'}]
    ) as mock_get_pdfs:
        with patch.object(requests, 'get', return_value=mock_response):
            email = involuntary_dissolution_stage_1_notification.process(message_payload, token)

            assert email['content']['subject'] == f'Attention {business_identifier} - Test Business'
            assert email['recipients'] == 'test@test.com'
            body = email['content']['body']
            assert body
            if test_name == 'TEST_XPRO_NO_AR':
                assert 'Notice of Commencement of Cancellation' in body
            else:
                assert 'Notice of Commencement of Dissolution' in body
            assert email['content']['attachments']
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1] == business
            assert mock_get_pdfs.call_args[0][2] == furnishing
