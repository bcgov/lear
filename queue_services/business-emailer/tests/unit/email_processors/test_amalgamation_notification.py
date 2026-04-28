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
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Filing

from business_emailer.email_processors import amalgamation_notification
from tests.unit import prep_amalgamation_filing


@pytest.mark.parametrize('status', [
    Filing.Status.PAID.value,
    Filing.Status.COMPLETED.value
])
def test_amalgamation_notification(app, session, mocker, status):
    """Assert Amalgamation notification is created."""
    # setup filing + business for email
    legal_name = 'test business'
    filing = prep_amalgamation_filing(session, 'BC1234567', '1', status, legal_name)
    token = 'token'
    # test processor
    mocker.patch(
        'business_emailer.email_processors.amalgamation_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(amalgamation_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = amalgamation_notification.process(
            {'filingId': filing.id, 'type': 'amalgamationApplication', 'option': status}, token)

        assert 'test@test.com' in email['recipients']
        if status == Filing.Status.PAID.value:
            assert email['content']['subject'] == legal_name + ' - Amalgamation'
            assert 'comp_party@email.com' in email['recipients']
        else:
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
            assert email['content']['subject'] == legal_name + ' - Confirmation of Amalgamation'

        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][3] == filing


def test_amalgamation_notification_paid_without_business(app, session, mocker):
    """Assert PAID amalgamation falls back to nameRequest when filing has no business_id."""
    legal_name = 'test business'
    filing = prep_amalgamation_filing(session, 'BC1234567', '1', Filing.Status.PAID.value, legal_name)
    filing.business_id = None
    filing.save()
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.amalgamation_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(amalgamation_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = amalgamation_notification.process(
            {'filingId': filing.id, 'type': 'amalgamationApplication', 'option': Filing.Status.PAID.value}, token)

        assert 'test@test.com' in email['recipients']
        assert 'comp_party@email.com' in email['recipients']
        assert email['content']['subject'] == legal_name + ' - Amalgamation'
        assert email['content']['body']
        # business dict passed to _get_pdfs should come from nameRequest with temp_reg identifier
        passed_business = mock_get_pdfs.call_args[0][2]
        assert passed_business['legalName'] == legal_name
        assert passed_business['identifier'] == filing.temp_reg


def test_amalgamation_attachments_paid(session, mocker, config):
    """PAID regular: Amalgamation Application (Regular) PDF + receipt."""
    identifier = 'BC1234567'
    filing = prep_amalgamation_filing(session, identifier, '1', Filing.Status.PAID.value, 'test business')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.amalgamation_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/amalgamationApplication',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=b'pdf_content_2',
            status_code=201,
        )
        output = amalgamation_notification.process(
            {'filingId': filing.id, 'type': 'amalgamationApplication', 'option': Filing.Status.PAID.value}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Amalgamation Application (Regular).pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_amalgamation_attachments_completed(session, mocker, config):
    """COMPLETED: Certificate Of Amalgamation + Notice of Articles."""
    identifier = 'BC1234567'
    filing = prep_amalgamation_filing(session, identifier, '1', Filing.Status.COMPLETED.value, 'test business')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.amalgamation_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/certificateOfAmalgamation',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/noticeOfArticles',
            content=b'pdf_content_2',
            status_code=200,
        )
        output = amalgamation_notification.process(
            {'filingId': filing.id, 'type': 'amalgamationApplication', 'option': Filing.Status.COMPLETED.value},
            token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Certificate Of Amalgamation.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Notice of Articles.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
