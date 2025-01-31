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
"""The Unit Tests for Notice of Withdrawal email processor."""
from unittest.mock import patch

import pytest
from legal_api.models import RegistrationBootstrap
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    CHANGE_OF_ADDRESS,
    CONTINUATION_IN,
    DISSOLUTION,
    INCORPORATION,
)

from entity_emailer.email_processors import notice_of_withdrawal_notification
from tests.unit import create_business, create_future_effective_filing, prep_notice_of_withdraw_filing


@pytest.mark.parametrize(
        'status, legal_name, legal_type, withdrawn_filing_type, withdrawn_filing_json, is_temp', [
            ('COMPLETED', 'test business', 'BC', 'incorporationApplication', INCORPORATION, True),
            ('PAID', 'test business', 'BC', 'incorporationApplication', INCORPORATION, True),
            ('COMPLETED', '1234567 B.C. INC.', 'BEN', 'continuationIn', CONTINUATION_IN, True),
            ('COMPLETED', 'test business', 'CBEN', 'amalgamationApplication', AMALGAMATION_APPLICATION, True),
            ('COMPLETED', 'test business', 'BC', 'changeOfAddress', CHANGE_OF_ADDRESS, False),
            ('PAID', 'test business', 'BC', 'changeOfAddress', CHANGE_OF_ADDRESS, False),
            ('COMPLETED', '1234567 B.C. INC.', 'BEN', 'alteration', ALTERATION_FILING_TEMPLATE, False),
            ('COMPLETED', '1234567 B.C. INC.', 'CBEN', 'dissolution', DISSOLUTION, False)
        ]
)
def test_notice_of_withdrawal_notification(
        app, session, status, legal_name, legal_type, withdrawn_filing_type, withdrawn_filing_json, is_temp):
    """Assert that the notice of withdrawal email processor works as expected."""
    business = None
    if is_temp:
        identifier = 'Tb31yQIuBw'
        temp_reg = RegistrationBootstrap()
        temp_reg._identifier = identifier
        temp_reg.save()
    else:
        identifier = 'BC1234567'
        business = create_business(identifier, legal_type, legal_name)

    business_id = business.id if business else None
    # setup withdrawn filing (FE filing) for NoW
    fe_filing = create_future_effective_filing(
        identifier, legal_type, legal_name, withdrawn_filing_type, withdrawn_filing_json, is_temp, business_id)
    now_filing = prep_notice_of_withdraw_filing(identifier, '1', legal_type, legal_name, business_id, fe_filing)
    token = 'token'

    # test NoW email processor
    with patch.object(notice_of_withdrawal_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(notice_of_withdrawal_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = notice_of_withdrawal_notification.process(
                {'filingId': now_filing.id, 'type': 'noticeOfWithdrawal', 'option': status}, token
            )
            if status != 'COMPLETED':
                assert email == {}
            else:
                if is_temp:
                    assert email['content']['subject'] == 'Notice of Withdrawal filed Successfully'
                else:
                    assert email['content']['subject'] == f'{legal_name} - Notice of Withdrawal filed Successfully'

                assert 'recipient@email.com' in email['recipients']
                assert email['content']['body']
                assert email['content']['attachments'] == []
                assert mock_get_pdfs.call_args[0][0] == token
                assert mock_get_pdfs.call_args[0][1]['identifier'] == identifier
                assert mock_get_pdfs.call_args[0][1]['legalName'] == legal_name
                assert mock_get_pdfs.call_args[0][1]['legalType'] == legal_type
                assert mock_get_pdfs.call_args[0][2] == now_filing
