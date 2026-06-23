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
import copy
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business
from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE

from business_emailer.email_processors import filing_notification
from tests.unit import create_filing, prep_incorp_filing, prep_maintenance_filing
from tests.unit.helpers import generate_temp_filing, make_future_effective, make_non_future_effective


def _prep_numbered_incorp_filing(session, identifier, payment_id, legal_type):
    """Return a PAID IA filing for a numbered company (business has no legal name in DB)."""
    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template['filing']['business'] = {'identifier': identifier}
    if legal_type:
        filing_template['filing']['business']['legalType'] = legal_type
        filing_template['filing']['incorporationApplication']['nameRequest']['legalType'] = legal_type
    for party in filing_template['filing']['incorporationApplication']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['incorporationApplication']['contactPoint']['email'] = 'test@test.com'
    # Remove legalName from nameRequest to ensure numbered path
    filing_template['filing']['incorporationApplication']['nameRequest'].pop('legalName', None)

    temp_identifier = generate_temp_filing()
    filing = create_filing(
        token=payment_id,
        filing_json=filing_template,
        business_id=None,
        bootstrap_id=temp_identifier,
    )
    filing.payment_completion_date = filing.filing_date
    filing.save()
    return filing


# ---------------------------------------------------------------------------
# test_incorp_notification (split from original parametrized test)
# ---------------------------------------------------------------------------

def test_incorp_notification_completed(app, session, mocker):
    """Assert that IA COMPLETED returns an email with the Successful Incorporation subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', 'BC')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

        assert email is not None
        assert email['content']['subject'] == 'test business - Successful Incorporation'
        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == 'COMPLETED'
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
        assert mock_get_pdfs.call_args[0][2]['legalType'] == 'BC'
        assert mock_get_pdfs.call_args[0][3] == filing


def test_incorp_notification_paid_non_future_returns_none(app, session, mocker):
    """Assert that IA PAID non-future-effective returns None (no email sent)."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_non_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        result = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert result is None


def test_incorp_notification_paid_future_effective(app, session, mocker):
    """Assert that IA PAID future-effective returns an email with the Filed subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert email is not None
    assert 'Incorporation Application Filed' in email['content']['subject']
    assert email['content']['body']
    assert email['content']['attachments'] == []
    assert mock_get_pdfs.call_args[0][0] == 'PAID'
    assert mock_get_pdfs.call_args[0][1] == token
    assert mock_get_pdfs.call_args[0][3] == filing


# ---------------------------------------------------------------------------
# test_numbered_incorp_notification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('legal_type', [
    ('BEN'),
    ('BC'),
    ('ULC'),
    ('CC'),
])
def test_numbered_incorp_notification_future_effective(app, session, mocker, legal_type):
    """Assert that future-effective PAID IA with no legal name uses the numbered description as business_name."""
    # Create a filing where the business has no legal name (numbered company scenario)
    filing = _prep_numbered_incorp_filing(session, 'BC1234567', '1', legal_type)
    make_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert email is not None
    assert email['content']['body']
    # When legalName is absent from the DB business:
    # - falls back to numberedDescription as business_name in subject
    # - falls back to 'Not Available' in the tombstone
    numbered_description = Business.BUSINESSES[Business.LegalTypes(legal_type)]['numberedDescription']
    assert numbered_description in email['content']['subject']
    assert "Business Name: Not Available" not in email['content']['body']


@pytest.mark.parametrize('legal_type', [
    ('BEN'),
    ('BC'),
    ('ULC'),
    ('CC'),
])
def test_numbered_incorp_notification_completed(app, session, mocker, legal_type):
    """Assert that for a COMPLETED IA the business legalName is used in the subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', legal_type=legal_type)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    assert email is not None
    assert email['content']['body']
    assert 'test business - Successful Incorporation' == email['content']['subject']


# ---------------------------------------------------------------------------
# test_maintenance_notification
# ---------------------------------------------------------------------------

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
    """Assert that maintenance filings produce an email with the correct recipients and attachments."""
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


def test_filing_attachments_ia_paid_future_effective(session, mocker, config):
    """IA PAID future-effective: filing PDF + receipt are attached."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'PAID', 'BC')
    make_future_effective(filing)
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

    assert output is not None
    attachments = output['content']['attachments']
    # IA always adds the filing application PDF + receipt.
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Incorporation Application.pdf'
    assert attachments[0]['attachOrder'] == '1'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert attachments[1]['attachOrder'] == '2'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_filing_attachments_ia_paid_non_future_returns_none(session, mocker, config):
    """IA PAID non-future-effective: process returns None (no email is sent)."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'PAID', 'BC')
    make_non_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    result = filing_notification.process(
        {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert result is None


def test_filing_attachments_ia_completed_bc(session, mocker, config):
    """IA COMPLETED BC: IncorporationApplication + Notice of Articles + Certificate of Incorporation + Receipt."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'BC')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/incorporationApplication',
            content=b'pdf_content_0',
            status_code=200,
        )
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
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=b'pdf_content_3',
            status_code=201,
        )
        output = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    # IA COMPLETED BC: IncorporationApplication + NOA + Certificate + Receipt = 4 attachments
    assert len(attachments) == 4
    file_names = [a['fileName'] for a in attachments]
    assert 'Incorporation Application.pdf' in file_names
    assert 'Notice of Articles.pdf' in file_names
    # New _add_filing_document_pdf replaces " Of " -> " of " (lowercase "of")
    assert 'Certificate of Incorporation.pdf' in file_names
    assert 'Receipt.pdf' in file_names


def test_filing_attachments_ia_completed_coop(session, mocker, config):
    """IA COMPLETED COOP: IncorporationApplication + Certificate + Certified Rules + Memorandum + Receipt."""
    identifier = 'CP1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'CP')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with requests_mock.Mocker() as m:
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/incorporationApplication',
            content=b'pdf_content_0',
            status_code=200,
        )
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
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=b'pdf_content_4',
            status_code=201,
        )
        output = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    # IA COMPLETED COOP: IncorporationApplication + Certificate + Rules + Memorandum + Receipt = 5 attachments
    assert len(attachments) == 5
    file_names = [a['fileName'] for a in attachments]
    assert 'Incorporation Application.pdf' in file_names
    # New _add_filing_document_pdf replaces " Of " -> " of " (lowercase "of")
    assert 'Certificate of Incorporation.pdf' in file_names
    assert 'Certified Rules.pdf' in file_names
    # New naming: "Memorandum.pdf" (NOT "Certified Memorandum.pdf")
    assert 'Memorandum.pdf' in file_names
    assert 'Receipt.pdf' in file_names


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
    # _add_filing_document_pdf replaces " Of " -> " of " so "changeOfAddress" -> "Change of Address"
    assert attachments[0]['fileName'] == 'Change of Address.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'


def test_filing_attachments_annual_report_paid(session, mocker, config):
    """annualReport PAID: filing PDF (prefixed with the AR year) + receipt."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'PAID', 'annualReport')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, 'get_recipients', return_value='test@test.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/annualReport',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.post(
                f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                content=b'pdf_content_2',
                status_code=201,
            )
            output = filing_notification.process(
                {'filingId': filing.id, 'type': 'annualReport', 'option': 'PAID'}, token)

    attachments = output['content']['attachments']
    # annualReport PAID: filing application PDF + receipt
    assert len(attachments) == 2
    # _add_filing_document_pdf prefixes the AR filing PDF with the annualReportDate year (2018-04-08 -> 2018)
    assert attachments[0]['fileName'] == '2018 Annual Report.pdf'
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


def test_ia_future_effective_paid_body_contains_tombstone_fields(app, session, mocker):
    """Assert that IA future-effective PAID body contains business name and incorporation number."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert email is not None
    body = email['content']['body']
    # The future template includes business-tombstone.md which renders these labels
    assert 'Business Name:' in body
    assert 'Incorporation Number:' in body
    # The future template includes what-happens-next.md
    assert 'What happens next' in body
    # Subject uses the "Filed" format
    assert 'Incorporation Application Filed' in email['content']['subject']


def test_ia_completed_body_and_subject(app, session, mocker):
    """Assert that IA COMPLETED body uses non-future template and subject is Successful Incorporation."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', 'BC')
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    assert email is not None
    body = email['content']['body']
    assert 'successfully incorporated' in body
    assert email['content']['subject'] == 'test business - Successful Incorporation'


@pytest.mark.parametrize("legal_type, tax_id, expected", [
    ("BC", "123456789BC0001", "123456789 BC0001"),
    ("BC", "123456789", "Not Available"),
    ("BC", None, "Not Available"),
    ("CP", None, None),
], ids=["BC with bn15", "BC with bn9", "BC with no bn", "CP doesn't show bn"])
def test_business_number_rendering(app, session, mocker, legal_type, tax_id, expected):
    """Assert business number renders as expected."""
    identifier = f'{legal_type}1234567'

    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', legal_type)
    business = Business.find_by_identifier(identifier)
    business.tax_id = tax_id
    business.save()

    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'COMPLETED'}, token)

    assert email is not None
    body = email['content']['body']
    if expected:
        assert f'**Business Number:** {expected}' in body
    else:
        assert '**Business Number:**' not in body


def test_future_attachments_list_in_ia_future_effective_paid_coop(app, session, mocker):
    """Assert that CP future_attachments_list is used for COOP future-effective PAID IA."""
    filing = prep_incorp_filing(session, 'CP1234567', '1', 'PAID', 'CP')
    make_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert email is not None
    body = email['content']['body']
    # CP future attachments include Memorandum and Certified Rules (not Notice of Articles)
    assert 'Memorandum' in body
    assert 'Certified Rules' in body


def test_future_attachments_list_in_ia_future_effective_paid_corp(app, session, mocker):
    """Assert that CORP future_attachments_list is used for non-COOP future-effective PAID IA."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_future_effective(filing)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        email = filing_notification.process(
            {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'PAID'}, token)

    assert email is not None
    body = email['content']['body']
    # CORP future attachments include Notice of Articles but not Memorandum
    assert 'Notice of Articles' in body
    assert 'Memorandum' not in body


@pytest.mark.parametrize(['filing_type', 'body_snippets', 'subject'], [
    (
        'annualReport',
        ['Confirmation of Annual Report from the Business Registry',
         'You have successfully filed your 2018 Annual Report with the BC Business Registry.',
         '2018 Annual Report'],
        'test business - Confirmation of Annual Report',
    ),
    (
        'changeOfDirectors',
        ['Confirmation of Director Change from the Business Registry',
         'You have successfully filed your Director Change with the BC Business Registry.'],
        'test business - Confirmation of Director Change',
    ),
    (
        'changeOfAddress',
        ['Confirmation of Address Change from the Business Registry',
         'You have successfully filed your Address Change with the BC Business Registry.'],
        'test business - Confirmation of Address Change',
    ),
])
def test_maintenance_filing_renders_body_and_subject(app, session, mocker, filing_type, body_snippets, subject):
    """Assert AR, director change and address change PAID emails render the expected body and subject."""
    filing = prep_maintenance_filing(session, 'BC1234567', '1', 'PAID', filing_type)
    token = 'token'
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_user_email_from_auth',
        return_value='user@email.com')
    mocker.patch(
        'business_emailer.email_processors.filing_notification.get_entity_dashboard_url',
        return_value='https://dummyurl.gov.bc.ca')
    with patch.object(filing_notification, '_get_pdfs', return_value=[]):
        with patch.object(filing_notification, 'get_recipients', return_value='test@test.com'):
            email = filing_notification.process(
                {'filingId': filing.id, 'type': filing_type, 'option': 'PAID'}, token)

    assert email is not None
    body = email['content']['body']
    for snippet in body_snippets:
        assert snippet in body
    assert not ".html]]" in body
    assert not ".md]]" in body
    assert email['content']['subject'] == subject
