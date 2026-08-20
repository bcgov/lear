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
from business_model.models import Furnishing

from business_emailer.email_processors import involuntary_dissolution_stage_1_notification
from tests.unit import create_business, create_furnishing  # noqa: I003


def create_test_business(identifier, legal_type):
    """Return a test business, bypassing the identifier setter for expro 'A' identifiers it rejects."""
    business = create_business('BC1234567', legal_type, 'Test Business')
    if identifier != 'BC1234567':
        business._identifier = identifier
        business.save()
    return business


@pytest.mark.parametrize(
        'test_name, business_identifier, legal_type, furnishing_name, action, reason_title, attachment_name', [
            ('TEST_BC_NO_AR', 'BC1234567', 'BC', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
             'dissolved', 'overdue annual reports',
             'Notice of Commencement of Dissolution'),
            ('TEST_XPRO_NO_AR', 'A1234567', 'A', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
             'cancelled', 'overdue annual reports',
             'Notice of Commencement of Cancellation'),
            ('TEST_BC_NO_TR', 'BC1234567', 'BC', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR,
             'dissolved', 'failure to file a post restoration transition application',
             'Notice of Commencement of Dissolution'),
            ('TEST_XPRO_NO_TR', 'A1234567', 'A', Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO,
             'cancelled', 'failure to file a post restoration transition application',
             'Notice of Commencement of Cancellation'),
        ]
)
def test_involuntary_dissolution_stage_1_notification(app, session, test_name, business_identifier, legal_type,
                                                      furnishing_name, action, reason_title, attachment_name):
    """Assert that the test_involuntary_dissolution_stage_1_notification can be processed."""
    token = 'token'
    business = create_test_business(business_identifier, legal_type)
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

            assert email['content']['subject'] == \
                f'Test Business - URGENT - Your business is in the process of being {action}'
            assert email['recipients'] == 'test@test.com'
            body = email['content']['body']
            assert body
            assert f'Your business is in the process of being {action} for {reason_title}' in body
            assert '**Business Name:** Test Business' in body
            if legal_type == 'A':
                assert f'**Registration Number:** {business_identifier}' in body
            else:
                assert f'**Incorporation Number:** {business_identifier}' in body
            assert '## Attention' in body
            assert f'Your business is in the process of being {action} because' in body
            assert '## Next Steps' in body
            assert f'you can request a delay of {"cancellation" if action == "cancelled" else "dissolution"}' in body
            assert '## Attachments' in body
            assert attachment_name in body
            # no MRAS registrations mocked, so no extraprovincial sentence
            assert 'Our records indicate' not in body
            assert '.md]]' not in body
            assert email['content']['attachments']
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1] == business
            assert mock_get_pdfs.call_args[0][2] == furnishing


@pytest.mark.parametrize(
        'test_name, jurisdictions, expected_display', [
            ('AB', [('AB', 'Alberta')], 'Alberta'),
            ('MB', [('MB', 'Manitoba')], 'Manitoba'),
            ('SK', [('SK', 'Saskatchewan')], 'Saskatchewan'),
            ('AB_MB', [('AB', 'Alberta'), ('MB', 'Manitoba')], 'Alberta and Manitoba'),
            ('AB_SK', [('AB', 'Alberta'), ('SK', 'Saskatchewan')], 'Alberta and Saskatchewan'),
            ('MB_SK', [('MB', 'Manitoba'), ('SK', 'Saskatchewan')], 'Manitoba and Saskatchewan'),
            ('AB_MB_SK', [('AB', 'Alberta'), ('MB', 'Manitoba'), ('SK', 'Saskatchewan')],
             'Alberta, Manitoba, and Saskatchewan'),
        ]
)
def test_involuntary_dissolution_stage_1_notification_extra_provincials(app, session, test_name,
                                                                        jurisdictions, expected_display):
    """Assert that NWPTA registrations render the foreign jurisdiction sentence in the Attention block."""
    token = 'token'
    business_identifier = 'BC1234567'
    business = create_business(business_identifier, 'BC', 'Test Business')
    furnishing = create_furnishing(session, business=business,
                                   furnishing_name=Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR)
    message_payload = {
        'furnishing': {
            'type': 'INVOLUNTARY_DISSOLUTION',
            'furnishingId': furnishing.id,
            'furnishingName': furnishing.furnishing_name
        }
    }

    # non-NWPTA jurisdictions must be filtered out of the display
    mras_jurisdictions = [{'id': j_id, 'name': name} for j_id, name in jurisdictions]
    mras_jurisdictions.append({'id': 'BC', 'name': 'British Columbia'})

    with patch.object(involuntary_dissolution_stage_1_notification, '_get_pdfs', return_value=[]):
        with patch.object(involuntary_dissolution_stage_1_notification, 'get_jurisdictions',
                          return_value={'jurisdictions': mras_jurisdictions}):
            email = involuntary_dissolution_stage_1_notification.process(message_payload, token)

            body = email['content']['body']
            assert f'Our records indicate your business is registered in {expected_display} ' \
                   'as an extraprovincial company.' in body
            assert f'its registration as an extraprovincial company in {expected_display} ' \
                   'will automatically be cancelled as well' in body
            assert 'British Columbia' not in body


def test_involuntary_dissolution_stage_1_notification_xpro_skips_mras(app, session):
    """Assert that XPRO furnishings do not look up MRAS jurisdictions."""
    token = 'token'
    business = create_test_business('A1234567', 'A')
    furnishing = create_furnishing(session, business=business,
                                   furnishing_name=Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO)
    message_payload = {
        'furnishing': {
            'type': 'INVOLUNTARY_DISSOLUTION',
            'furnishingId': furnishing.id,
            'furnishingName': furnishing.furnishing_name
        }
    }

    with patch.object(involuntary_dissolution_stage_1_notification, '_get_pdfs', return_value=[]):
        with patch.object(involuntary_dissolution_stage_1_notification, 'get_jurisdictions') as mock_get_jurisdictions:
            email = involuntary_dissolution_stage_1_notification.process(message_payload, token)

            mock_get_jurisdictions.assert_not_called()
            assert 'Our records indicate' not in email['content']['body']
