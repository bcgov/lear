# Copyright © 2020 Province of British Columbia
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
"""The Unit Tests for the Incorporation email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business

from business_emailer.email_processors import filing_notification
from tests.unit import prep_incorp_filing, prep_maintenance_filing


@pytest.mark.parametrize('status', [
    ('PAID'),
    ('COMPLETED'),
])
def test_incorp_notification(app, session, mocker, status):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', '1', status, 'BC')
    token = 'token'
    # test processor
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': status}, token)
        if status == 'PAID':
            assert 'comp_party@email.com' in email['recipients']
            assert email['content']['subject'] == 'Confirmation of Filing from the Business Registry'
        else:
            assert email['content']['subject'] == 'Incorporation Documents from the Business Registry'

        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        if status == 'COMPLETED':
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'

        assert mock_get_pdfs.call_args[0][2]['legalType'] == 'BC'
        assert mock_get_pdfs.call_args[0][3] == filing


@pytest.mark.parametrize('legal_type', [
    ('BEN'),
    ('BC'),
    ('ULC'),
    ('CC'),
])
def test_numbered_incorp_notification(app, session, mocker, legal_type):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', legal_type=legal_type)
    token = 'token'
    # test processor
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

        assert email['content']['body']
        assert Business.BUSINESSES[legal_type]['numberedDescription'] in email['content']['body']


@pytest.mark.parametrize(['status', 'filing_type', 'submitter_role'], [
    ('PAID', 'annualReport', None),
    ('PAID', 'changeOfAddress', None),
    ('PAID', 'changeOfDirectors', None),
    ('PAID', 'alteration', None),
    ('COMPLETED', 'changeOfAddress', None),
    ('COMPLETED', 'changeOfDirectors', None),
    ('COMPLETED', 'alteration', None),
    ('COMPLETED', 'alteration', 'staff')
])
def test_maintenance_notification(app, session, mocker, status, filing_type, submitter_role):
    """Assert that the legal name is changed."""
    # setup filing + business for email
    filing = prep_maintenance_filing(session, 'BC1234567', '1', status, filing_type, submitter_role=submitter_role)
    token = 'token'
    # test processor
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_user_email_from_auth',
        return_value='user@email.com')
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(filing_notification, 'get_recipients', return_value='test@test.com') \
                as mock_get_recipients:
            email = filing_notification.process(
                {'filingId': filing.id, 'type': filing_type, 'option': status}, token)

            if filing_type == 'alteration':
                if submitter_role:
                    assert f'{submitter_role}@email.com' in email['recipients']
                else:
                    assert 'user@email.com' in email['recipients']

            assert 'test@test.com' in email['recipients']
            assert email['content']['body']
            assert email['content']['attachments'] == []
            assert mock_get_pdfs.call_args[0][0] == status
            assert mock_get_pdfs.call_args[0][1] == token
            assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
            assert mock_get_pdfs.call_args[0][2]['legalType'] == Business.LegalTypes.BCOMP.value
            assert mock_get_pdfs.call_args[0][2]['legalName'] == 'test business'
            assert mock_get_pdfs.call_args[0][3] == filing
            assert mock_get_recipients.call_args[0][0] == status
            assert mock_get_recipients.call_args[0][1] == filing.filing_json
            assert mock_get_recipients.call_args[0][2] == token


def test_filing_attachments_ia_paid(session, mocker, config):
    """IA PAID: filing PDF + receipt."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'PAID', 'BC')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/incorporationApplication',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=b'pdf_content_2',
            status_code=201,
        )
        output = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Incorporation Application.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_filing_attachments_ia_completed_bc(session, mocker, config):
    """IA COMPLETED BC: Notice of Articles + Certificate of Incorporation."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'BC')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/noticeOfArticles',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/certificateOfIncorporation',
            content=b'pdf_content_2',
            status_code=200,
        )
        output = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Notice of Articles.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Certificate Of Incorporation.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_filing_attachments_ia_completed_coop(session, mocker, config):
    """IA COMPLETED COOP: Certificate + Certified Rules + Certified Memorandum (no NOA)."""
    identifier = 'CP1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'CP')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/certificateOfIncorporation',
            content=b'pdf_content_1',
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/certifiedRules',
            content=b'pdf_content_2',
            status_code=200,
        )
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/memorandum',
            content=b'pdf_content_3',
            status_code=200,
        )
        output = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 3
    assert attachments[0]['fileName'] == 'Certificate Of Incorporation.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Certified Rules.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
    assert attachments[2]['fileName'] == 'Certified Memorandum.pdf'
    assert base64.b64decode(attachments[2]['fileBytes']).decode('utf-8') == 'pdf_content_3'


def test_filing_attachments_change_of_address_paid(session, mocker, config):
    """changeOfAddress PAID: filing PDF + receipt."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'PAID', 'changeOfAddress')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, 'get_recipients', return_value='test@test.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/changeOfAddress',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.post(
                f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                content=b'pdf_content_2',
                status_code=201,
            )
            output = filing_notification.process(
                {'filingId': filing.id, 'type': 'changeOfAddress', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Change Of Address.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_filing_attachments_alteration_completed_name_change(session, mocker, config):
    """alteration COMPLETED (BC, with name change): NOA + Certificate of Name Change."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'COMPLETED', 'alteration')
    # force the name-change branch via meta_data
    filing._meta_data = {'alteration': {'toLegalName': 'new name'}}
    filing.save()
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_user_email_from_auth',
        return_value='user@email.com')
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, 'get_recipients', return_value='test@test.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/noticeOfArticles',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/certificateOfNameChange',
                content=b'pdf_content_2',
                status_code=200,
            )
            output = filing_notification.process(
                {'filingId': filing.id, 'type': 'alteration', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Notice of Articles.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Certificate of Name Change.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
