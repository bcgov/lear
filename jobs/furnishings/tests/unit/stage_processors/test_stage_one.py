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

"""Tests for the Furnishings Job.

Test suite to ensure that the Furnishings Job is working as expected.
"""
import copy
from unittest.mock import MagicMock, patch

import pytest
import requests
from legal_api.models import Business, Furnishing
from legal_api.services.bootstrap import AccountService
from registry_schemas.example_data import FILING_HEADER, RESTORATION

from furnishings.stage_processors.stage_one import StageOneProcessor, process

from .. import factory_batch, factory_batch_processing, factory_business, factory_completed_filing


RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION


@pytest.mark.parametrize(
    'test_name, mock_return', [
        ('EMAIL', {'contacts': [{'email': 'test@no-reply.com'}]}),
        ('NO_EMAIL', {'contacts': []})
    ]
)
def test_get_email_address_from_auth(session, test_name, mock_return):
    """Assert that email address is returned."""
    token = 'token'
    mock_response = MagicMock()
    mock_response.json.return_value = mock_return
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(requests, 'get', return_value=mock_response):
            email = StageOneProcessor._get_email_address_from_auth('BC1234567')
            if test_name == 'NO_EMAIL':
                assert email is None
            else:
                assert email == 'test@no-reply.com'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_name, entity_type, email, expected_furnishing_name', [
        (
            'BC_AR_OVERDUE',
            Business.LegalTypes.COMP.value,
            'test@no-reply.com',
            Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR
        ),
        (
            'BC_TRANSITION_OVERDUE',
            Business.LegalTypes.COMP.value,
            'test@no-reply.com',
            Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR
        ),
        (
            'XP_AR_OVERDUE',
            Business.LegalTypes.EXTRA_PRO_A.value,
            'test@no-reply.com',
            Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO
        ),
        # the following is a temporary test case for business without email,
        # need modification after paper letter flow is added.
        (
            'NO_EMAIL_NO_FURNISHING_ENTRY',
            Business.LegalTypes.COMP.value,
            None,
            None
        )
    ]
)
async def test_stage_1_process_first_notification_email(app, session, test_name, entity_type, email, expected_furnishing_name):
    """Assert that email furnishing entry is created correctly."""
    business = factory_business(identifier='BC1234567', entity_type=entity_type)
    batch = factory_batch()
    factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=business.identifier,
    )
    if 'TRANSITION' in test_name:
        factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration')

    qsm = MagicMock()
    with patch.object(StageOneProcessor, '_get_email_address_from_auth', return_value=email):
        with patch.object(StageOneProcessor, '_send_email', return_value=None) as mock_send_email:
            await process(app, qsm)

            if email:
                mock_send_email.assert_called()
                furnishings = Furnishing.find_by(business_id=business.id)
                assert len(furnishings) == 1
                furnishing = furnishings[0]
                assert furnishing.furnishing_type == Furnishing.FurnishingType.EMAIL
                assert furnishing.email == 'test@no-reply.com'
                assert furnishing.furnishing_name == expected_furnishing_name
                assert furnishing.status == Furnishing.FurnishingStatus.QUEUED
                assert furnishing.grouping_identifier is not None
            else:
                mock_send_email.assert_not_called()
                furnishings = Furnishing.find_by(business_id=business.id)
                assert len(furnishings) == 0
