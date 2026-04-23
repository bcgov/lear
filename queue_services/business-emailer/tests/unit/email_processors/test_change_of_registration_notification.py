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
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business

from business_emailer.email_processors import change_of_registration_notification
from tests.unit import prep_change_of_registration_filing


@pytest.mark.parametrize('status,legal_type,submitter_role', [
    ('PAID', Business.LegalTypes.SOLE_PROP.value, None),
    ('COMPLETED', Business.LegalTypes.SOLE_PROP.value, None),
    ('PAID', Business.LegalTypes.PARTNERSHIP.value, None),
    ('COMPLETED', Business.LegalTypes.PARTNERSHIP.value, None),

    ('PAID', Business.LegalTypes.SOLE_PROP.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.SOLE_PROP.value, 'staff'),
    ('PAID', Business.LegalTypes.PARTNERSHIP.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.PARTNERSHIP.value, 'staff'),
])
def test_change_of_registration_notification(app, session, mocker, status, legal_type, submitter_role):
    """Assert that email attributes are correct."""
    # setup filing + business for email
    legal_name = 'test business'
    parties = [{
        'firstName': 'Jane',
        'lastName': 'Doe',
        'middleInitial': 'A',
        'partyType': 'person',
        'organizationName': ''
    }]
    filing = prep_change_of_registration_filing(session, 'FM1234567', '1', legal_type,
                                                legal_name, submitter_role, parties)
    token = 'token'
    # test processor
    mocker.patch(
        'business_emailer.email_processors.change_of_registration_notification.get_user_email_from_auth',
        return_value='user@email.com')
    with patch.object(change_of_registration_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = change_of_registration_notification.process(
            {'filingId': filing.id, 'type': 'changeOfRegistration', 'option': status}, token)
        if status == 'PAID':
            assert email['content']['subject'] == 'test business - Confirmation of Filing from the Business Registry'
        else:
            assert email['content']['subject'] == \
                'test business - Change of Registration Documents from the Business Registry'

        if submitter_role:
            assert f'{submitter_role}@email.com' in email['recipients']
        else:
            assert 'user@email.com' in email['recipients']

        if status == 'COMPLETED':
            assert 'no_one@never.get' in email['recipients']
            if legal_type == Business.LegalTypes.PARTNERSHIP.value:
                assert 'party@email.com' in email['recipients']

        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == 'COMPLETED':
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'FM1234567'
        assert mock_get_pdfs.call_args[0][3] == filing


def _cor_filing(session, identifier='FM1234567'):
    parties = [{
        'firstName': 'Jane', 'lastName': 'Doe', 'middleInitial': 'A',
        'partyType': 'person', 'organizationName': ''
    }]
    return prep_change_of_registration_filing(
        session, identifier, '1', Business.LegalTypes.SOLE_PROP.value, 'test business', None, parties)


def test_change_of_registration_attachments_paid(session, mocker, config):
    """Assert PAID path attaches the filing PDF and the receipt."""
    identifier = 'FM1234567'
    filing = _cor_filing(session, identifier)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.change_of_registration_notification.get_user_email_from_auth',
        return_value='user@email.com')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/changeOfRegistration',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=b'pdf_content_2',
            status_code=201,
        )
        output = change_of_registration_notification.process(
            {'filingId': filing.id, 'type': 'changeOfRegistration', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Change of Registration.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_change_of_registration_attachments_completed(session, mocker, config):
    """Assert COMPLETED path attaches only the Amended Registration Statement."""
    identifier = 'FM1234567'
    filing = _cor_filing(session, identifier)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.change_of_registration_notification.get_user_email_from_auth',
        return_value='user@email.com')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/amendedRegistrationStatement',
            content=b'pdf_content_1',
            status_code=200,
        )
        output = change_of_registration_notification.process(
            {'filingId': filing.id, 'type': 'changeOfRegistration', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 1
    assert attachments[0]['fileName'] == 'AmendedRegistrationStatement.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
