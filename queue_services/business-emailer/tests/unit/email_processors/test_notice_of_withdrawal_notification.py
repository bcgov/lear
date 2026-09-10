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
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import RegistrationBootstrap
from registry_schemas.example_data import (
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    CHANGE_OF_ADDRESS,
    CONTINUATION_IN,
    DISSOLUTION,
    INCORPORATION,
)

from business_emailer.email_processors import notice_of_withdrawal_notification
from tests.unit.helpers import generate_temp_filing
from tests.unit import create_business, create_future_effective_filing, prep_notice_of_withdraw_filing


@pytest.mark.parametrize(
        'status, legal_name, legal_type, withdrawn_filing_type, withdrawn_filing_json, is_temp, tax_id, '
        'withdrawn_filing_name', [
            ('COMPLETED', 'test business', 'BC', 'incorporationApplication', INCORPORATION, True, None,
             'Incorporation Application'),
            ('COMPLETED', '1234567 B.C. INC.', 'BEN', 'continuationIn', CONTINUATION_IN, True, None,
             'Continuation Application'),
            ('COMPLETED', 'test business', 'CBEN', 'amalgamationApplication', AMALGAMATION_APPLICATION, True, None,
             'Amalgamation Application'),
            ('COMPLETED', 'test business', 'BC', 'changeOfAddress', CHANGE_OF_ADDRESS, False, None,
             'Address Change'),
            ('COMPLETED', '1234567 B.C. INC.', 'BEN', 'alteration', ALTERATION_FILING_TEMPLATE, False, '123456789BC0001',
             'Alteration'),
            ('COMPLETED', '1234567 B.C. INC.', 'CBEN', 'dissolution', DISSOLUTION, False, '123456789',
             'Voluntary Dissolution Application')
        ]
)
def test_notice_of_withdrawal_notification(  # noqa: PLR0913
        app, session, status, legal_name, legal_type, withdrawn_filing_type, withdrawn_filing_json, is_temp, tax_id,
        withdrawn_filing_name):
    """Assert that the notice of withdrawal email processor works as expected."""
    business = None
    if is_temp:
        identifier = generate_temp_filing()
    else:
        identifier = 'BC1234567'
        business = create_business(identifier, legal_type, legal_name)
        business.tax_id = tax_id
        business.save()

    business_id = business.id if business else None
    # setup withdrawn filing (FE filing) for NoW
    fe_filing = create_future_effective_filing(
        identifier, legal_type, legal_name, withdrawn_filing_type, withdrawn_filing_json, is_temp, business_id)
    now_filing = prep_notice_of_withdraw_filing(identifier, '1', legal_type, legal_name, business_id, fe_filing)
    token = 'token'

    pdfs = [
        {'fileName': 'Notice of Withdrawal.pdf', 'fileBytes': '', 'fileUrl': '', 'attachOrder': '1'},
        {'fileName': 'Receipt.pdf', 'fileBytes': '', 'fileUrl': '', 'attachOrder': '2'}
    ]

    # test NoW email processor
    with patch.object(notice_of_withdrawal_notification, '_get_pdfs', return_value=pdfs) as mock_get_pdfs:
        with patch.object(notice_of_withdrawal_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = notice_of_withdrawal_notification.process(
                {'filingId': now_filing.id, 'type': 'noticeOfWithdrawal', 'option': status}, token
            )

            assert email['content']['subject'] == f'{legal_name} - Notice of Withdrawal filed Successfully'
            assert 'recipient@email.com' in email['recipients']
            assert email['content']['attachments'] == pdfs

            body = email['content']['body']
            assert f'# Your {withdrawn_filing_name} has been successfully withdrawn' in body
            assert f'**Business Name:** {legal_name}' in body
            if is_temp:
                # new business filings show the withdrawn filing id and no incorporation/business number
                assert f'**Filing Number:** {fe_filing.id}' in body
                assert '**Incorporation Number:**' not in body
                assert '**Business Number:**' not in body
            else:
                assert '**Filing Number:**' not in body
                assert f'**Incorporation Number:** {identifier}' in body
                if tax_id and len(tax_id) > 9:
                    assert '**Business Number:** 123456789 BC0001' in body
                else:
                    assert '**Business Number:**' not in body
            assert '**Withdrawal Date and Time:**' in body
            assert f'**Withdrawn Record:** {withdrawn_filing_name}' in body
            assert '## Attachments' in body
            assert '- Notice of Withdrawal' in body
            assert '- Receipt' in body
            assert f'({app.config.get("DASHBOARD_URL")}{identifier})' in body
            assert '## Business Registry' not in body
            assert '**Business Registry**' in body
            assert '.md]]' not in body
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1]['identifier'] == identifier
            assert mock_get_pdfs.call_args[0][1]['legalName'] == legal_name
            assert mock_get_pdfs.call_args[0][1]['legalType'] == legal_type
            assert mock_get_pdfs.call_args[0][2] == now_filing


def test_notice_of_withdrawal_attachments(session, config):
    """Assert _get_pdfs assembles the Notice of Withdrawal filing PDF and receipt."""
    identifier = 'BC1234567'
    legal_type = 'BC'
    legal_name = 'test business'
    business = create_business(identifier, legal_type, legal_name)
    fe_filing = create_future_effective_filing(
        identifier, legal_type, legal_name, 'changeOfAddress', CHANGE_OF_ADDRESS, False, business.id)
    now_filing = prep_notice_of_withdraw_filing(identifier, '1', legal_type, legal_name, business.id, fe_filing)
    token = 'token'
    with patch.object(notice_of_withdrawal_notification, 'get_recipient_from_auth',
                      return_value='recipient@email.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{now_filing.id}/documents/noticeOfWithdrawal',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.post(
                f'{config.get("PAY_API_URL")}/{now_filing.payment_token}/receipts',
                content=b'pdf_content_2',
                status_code=201,
            )
            output = notice_of_withdrawal_notification.process(
                {'filingId': now_filing.id, 'type': 'noticeOfWithdrawal', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Notice of Withdrawal.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
