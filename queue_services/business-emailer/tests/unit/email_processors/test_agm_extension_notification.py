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
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business

from business_emailer.email_processors import agm_extension_notification
from tests.unit import prep_agm_extension_filing


@pytest.mark.parametrize('status,legal_name,is_numbered', [
    ('COMPLETED', 'test business', False),
    ('COMPLETED', 'BC1234567', True),
])
def test_agm_extension_notification(app, session, status, legal_name, is_numbered):
    """Assert that the agm extension email processor works as expected."""
    # setup filing + business for email
    filing = prep_agm_extension_filing('BC1234567', '1', Business.LegalTypes.COMP.value, legal_name)
    token = 'token'
    # test processor
    with patch.object(agm_extension_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(agm_extension_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = agm_extension_notification.process(
                {'filingId': filing.id, 'type': 'agmExtension', 'option': status}, token)

            if (is_numbered):
                assert email['content']['subject'] == \
                    'Numbered Company - AGM Extension Documents from the Business Registry'
            else:
                assert email['content']['subject'] == \
                    legal_name + ' - AGM Extension Documents from the Business Registry'

            assert 'recipient@email.com' in email['recipients']
            assert email['content']['body']
            assert email['content']['attachments'] == []
            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1]['identifier'] == 'BC1234567'
            assert mock_get_pdfs.call_args[0][1]['legalName'] == legal_name
            assert mock_get_pdfs.call_args[0][1]['legalType'] == Business.LegalTypes.COMP.value
            assert mock_get_pdfs.call_args[0][2] == filing


def test_agm_extension_attachments(session, config):
    """Assert _get_pdfs assembles the AGM Extension letter and receipt."""
    identifier = 'BC1234567'
    filing = prep_agm_extension_filing(
        identifier, '1', Business.LegalTypes.COMP.value, 'test business')
    token = 'token'
    with patch.object(agm_extension_notification, 'get_recipient_from_auth',
                      return_value='recipient@email.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/letterOfAgmExtension',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.post(
                f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                content=b'pdf_content_2',
                status_code=201,
            )
            output = agm_extension_notification.process(
                {'filingId': filing.id, 'type': 'agmExtension', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Letter of AGM Extension Approval.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
