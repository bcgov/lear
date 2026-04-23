# Copyright © 2021 Province of British Columbia
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
"""The Unit Tests for the Dissolution email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business

from business_emailer.email_processors import dissolution_notification
from tests.unit import prep_dissolution_filing


@pytest.mark.parametrize('status,legal_type,submitter_role', [
    ('PAID', Business.LegalTypes.COMP.value, None),
    ('COMPLETED', Business.LegalTypes.COMP.value, None),
    ('PAID', Business.LegalTypes.BCOMP.value, None),
    ('COMPLETED', Business.LegalTypes.BCOMP.value, None),
    ('PAID', Business.LegalTypes.BC_CCC.value, None),
    ('COMPLETED', Business.LegalTypes.BC_CCC.value, None),
    ('PAID', Business.LegalTypes.BC_ULC_COMPANY.value, None),
    ('COMPLETED', Business.LegalTypes.BC_ULC_COMPANY.value, None),
    ('PAID', Business.LegalTypes.COOP.value, None),
    ('COMPLETED', Business.LegalTypes.COOP.value, None),

    ('PAID', Business.LegalTypes.COMP.value, 'staff'),
    ('COMPLETED', Business.LegalTypes.COMP.value, 'staff'),
])
def test_dissolution_notification(app, session, status, legal_type, submitter_role):
    """Assert that the dissolution email processor for corps works as expected."""
    # setup filing + business for email
    legal_name = 'test business'
    filing = prep_dissolution_filing(session, 'BC1234567', '1', status, legal_type, legal_name, submitter_role)
    token = 'token'
    # test processor
    with patch.object(dissolution_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
            with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
                email = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': status}, token)
                if status == 'PAID':
                    assert email['content']['subject'] == legal_name + ' - Voluntary dissolution'
                else:
                    assert email['content']['subject'] == \
                        legal_name + ' - Confirmation of Dissolution from the Business Registry'

                if submitter_role:
                    assert f'{submitter_role}@email.com' in email['recipients']
                else:
                    assert 'user@email.com' in email['recipients']
                assert 'recipient@email.com' in email['recipients']
                assert 'custodian@email.com' in email['recipients']
                assert email['content']['body']
                assert email['content']['attachments'] == []
                assert mock_get_pdfs.call_args[0][0] == status
                assert mock_get_pdfs.call_args[0][1] == token
                assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
                assert mock_get_pdfs.call_args[0][2]['legalName'] == legal_name
                assert mock_get_pdfs.call_args[0][2]['legalType'] == legal_type
                assert mock_get_pdfs.call_args[0][3] == filing


@pytest.mark.parametrize('status,legal_type,submitter_role', [
    ('PAID', Business.LegalTypes.SOLE_PROP.value, None),
    ('COMPLETED', Business.LegalTypes.SOLE_PROP.value, None),
    ('PAID', Business.LegalTypes.PARTNERSHIP.value, None),
    ('COMPLETED', Business.LegalTypes.PARTNERSHIP.value, None),
])
def test_firms_dissolution_notification(app, session, status, legal_type, submitter_role):
    """Assert that the dissolution email processor for firms works as expected."""
    # setup filing + business for email
    legal_name = 'test business'
    parties = [{
        'firstName': 'Jane',
        'lastName': 'Doe',
        'middleInitial': 'A',
        'partyType': 'person',
        'organizationName': ''
    }]
    filing = prep_dissolution_filing(session, 'FM1234567', '1', status, legal_type, legal_name, submitter_role, parties)
    token = 'token'
    # test processor
    with patch.object(dissolution_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
            with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
                email = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': status}, token)
                if status == 'PAID':
                    assert email['content']['subject'] == \
                        f'{legal_name} - Confirmation of Filing from the Business Registry'
                else:
                    assert email['content']['subject'] == \
                        f'{legal_name} - Dissolution Documents from the Business Registry'

                if submitter_role:
                    assert f'{submitter_role}@email.com' in email['recipients']
                else:
                    assert 'user@email.com' in email['recipients']
                assert 'recipient@email.com' in email['recipients']
                assert 'cp@email.com' in email['recipients']
                assert email['content']['body']
                assert email['content']['attachments'] == []
                assert mock_get_pdfs.call_args[0][0] == status
                assert mock_get_pdfs.call_args[0][1] == token
                assert mock_get_pdfs.call_args[0][2]['identifier'] == 'FM1234567'
                assert mock_get_pdfs.call_args[0][2]['legalName'] == 'JANE A DOE'
                assert mock_get_pdfs.call_args[0][2]['legalType'] == legal_type
                assert mock_get_pdfs.call_args[0][3] == filing


def test_dissolution_attachments_paid_bc(session, config):
    """PAID BC: Voluntary Dissolution Application + receipt."""
    identifier = 'BC1234567'
    filing = prep_dissolution_filing(
        session, identifier, '1', 'PAID', Business.LegalTypes.COMP.value, 'test business', None)
    token = 'token'
    with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
        with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
            with requests_mock.Mocker() as m:
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/dissolution',
                    content=b'pdf_content_1',
                    status_code=200,
                )
                m.post(
                    f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                    content=b'pdf_content_2',
                    status_code=201,
                )
                output = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Voluntary Dissolution Application.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_dissolution_attachments_paid_sp_receipt_only(session, config):
    """PAID SP: no filing PDF (SP/GP excluded) — receipt only."""
    identifier = 'FM1234567'
    parties = [{
        'firstName': 'Jane', 'lastName': 'Doe', 'middleInitial': 'A',
        'partyType': 'person', 'organizationName': ''
    }]
    filing = prep_dissolution_filing(
        session, identifier, '1', 'PAID', Business.LegalTypes.SOLE_PROP.value,
        'test business', None, parties)
    token = 'token'
    with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
        with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
            with requests_mock.Mocker() as m:
                m.post(
                    f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                    content=b'pdf_content_1',
                    status_code=201,
                )
                output = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 1
    assert attachments[0]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'


def test_dissolution_attachments_completed_sp(session, config):
    """COMPLETED SP: Statement of Dissolution only."""
    identifier = 'FM1234567'
    parties = [{
        'firstName': 'Jane', 'lastName': 'Doe', 'middleInitial': 'A',
        'partyType': 'person', 'organizationName': ''
    }]
    filing = prep_dissolution_filing(
        session, identifier, '1', 'COMPLETED', Business.LegalTypes.SOLE_PROP.value,
        'test business', None, parties)
    token = 'token'
    with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
        with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
            with requests_mock.Mocker() as m:
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/dissolution',
                    content=b'pdf_content_1',
                    status_code=200,
                )
                output = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 1
    assert attachments[0]['fileName'] == 'Statement of Dissolution.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'


def test_dissolution_attachments_completed_bc(session, config):
    """COMPLETED BC (non-admin): Certificate of Dissolution."""
    identifier = 'BC1234567'
    filing = prep_dissolution_filing(
        session, identifier, '1', 'COMPLETED', Business.LegalTypes.COMP.value, 'test business', None)
    token = 'token'
    with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
        with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
            with requests_mock.Mocker() as m:
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/certificateOfDissolution',
                    content=b'pdf_content_1',
                    status_code=200,
                )
                output = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 1
    assert attachments[0]['fileName'] == 'Certificate of Dissolution.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'


def test_dissolution_attachments_completed_coop(session, config):
    """COMPLETED COOP: Certificate of Dissolution + Certified Affidavit + Certified Special Resolution."""
    identifier = 'CP1234567'
    filing = prep_dissolution_filing(
        session, identifier, '1', 'COMPLETED', Business.LegalTypes.COOP.value, 'test business', None)
    token = 'token'
    with patch.object(dissolution_notification, 'get_recipient_from_auth', return_value='recipient@email.com'):
        with patch.object(dissolution_notification, 'get_user_email_from_auth', return_value='user@email.com'):
            with requests_mock.Mocker() as m:
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/certificateOfDissolution',
                    content=b'pdf_content_1',
                    status_code=200,
                )
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/affidavit',
                    content=b'pdf_content_2',
                    status_code=200,
                )
                m.get(
                    f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                    f'/filings/{filing.id}/documents/specialResolution',
                    content=b'pdf_content_3',
                    status_code=200,
                )
                output = dissolution_notification.process(
                    {'filingId': filing.id, 'type': 'dissolution', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 3
    assert attachments[0]['fileName'] == 'Certificate of Dissolution.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Certified Affidavit.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
    assert attachments[2]['fileName'] == 'Certified Special Resolution.pdf'
    assert base64.b64decode(attachments[2]['fileBytes']).decode('utf-8') == 'pdf_content_3'
