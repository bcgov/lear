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
from tests.unit import (CONTACT_POINT, PARTY_EMAIL_1, PARTY_EMAIL_2,
                        create_filing, prep_change_of_registration_filing, prep_incorp_filing,
                        prep_maintenance_filing, prep_registration_filing)
from tests.unit.helpers import generate_temp_filing, make_future_effective, make_non_future_effective


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pdfs(mocker):
    """Patch get_pdfs to return no attachments; yields the mock for call_args assertions."""
    return mocker.patch.object(filing_notification, 'get_pdfs', return_value=[])


@pytest.fixture
def mock_recipients(mocker):
    """Patch get_recipients to return a fixed recipient; yields the mock for call_args assertions."""
    return mocker.patch.object(filing_notification, 'get_recipients', return_value='test@test.com')


@pytest.fixture
def mock_user_email(mocker):
    """Patch get_user_email_from_auth to return a fixed user email."""
    return mocker.patch.object(filing_notification, 'get_user_email_from_auth', return_value='user@email.com')


def process_filing(filing, filing_type, option, token='token'):
    """Run the filing_notification processor for the given filing."""
    return filing_notification.process(
        {'filingId': filing.id, 'type': filing_type, 'option': option}, token)


def assert_attachment(attachment, file_name, content=None, order=None):
    """Assert an attachment's file name and (optionally) its decoded content and attach order."""
    assert attachment['fileName'] == file_name
    if content is not None:
        assert base64.b64decode(attachment['fileBytes']).decode('utf-8') == content
    if order is not None:
        assert attachment['attachOrder'] == order


def mock_filing_docs(m, config, identifier, filing, doc_contents, receipt=b'receipt_content'):
    """Register the document GET mocks and the receipt POST mock for a filing.

    doc_contents maps document_type -> response bytes. Pass receipt=None to skip the receipt mock.
    """
    for doc_type, content in doc_contents.items():
        m.get(
            f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
            f'/filings/{filing.id}/documents/{doc_type}',
            content=content,
            status_code=200,
        )
    if receipt is not None:
        m.post(
            f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
            content=receipt,
            status_code=201,
        )


def firm_parties():
    """Return a fresh single-person FIRM party list."""
    return [{
        'firstName': 'Jane',
        'lastName': 'Doe',
        'middleInitial': 'A',
        'partyType': 'person',
        'organizationName': ''
    }]


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

def test_incorp_notification_completed(app, session, mock_pdfs):
    """Assert that IA COMPLETED returns an email with the Successful Incorporation subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', 'BC')
    token = 'token'
    email = process_filing(filing, 'incorporationApplication', 'COMPLETED')

    assert email is not None
    assert email['content']['subject'] == 'test business - Successful Incorporation'
    assert 'test@test.com' in email['recipients']
    assert email['content']['body']
    assert email['content']['attachments'] == []
    assert mock_pdfs.call_args[0][0] == token
    assert mock_pdfs.call_args[0][1]['identifier'] == 'BC1234567'
    assert mock_pdfs.call_args[0][1]['legalType'] == 'BC'
    assert mock_pdfs.call_args[0][2] == filing


def test_incorp_notification_paid_future_effective(app, session, mock_pdfs):
    """Assert that IA PAID future-effective returns an email with the Filed subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_future_effective(filing)
    token = 'token'
    email = process_filing(filing, 'incorporationApplication', 'PAID')

    assert email is not None
    assert 'Incorporation Application Filed' in email['content']['subject']
    assert email['content']['body']
    assert email['content']['attachments'] == []
    assert mock_pdfs.call_args[0][0] == token
    assert mock_pdfs.call_args[0][2] == filing


@pytest.mark.parametrize('filing_type', ['incorporationApplication', 'registration'])
def test_paid_non_future_effective_returns_none(app, session, filing_type):
    """Assert that a PAID non-future-effective filing returns None (no email is sent)."""
    if filing_type == 'incorporationApplication':
        filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
        make_non_future_effective(filing)
    else:
        filing = prep_registration_filing(
            session, 'FM1234567', '1', 'PAID', Business.LegalTypes.SOLE_PROP.value, 'test business')

    result = process_filing(filing, filing_type, 'PAID')

    assert result is None


# ---------------------------------------------------------------------------
# test_numbered_incorp_notification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('legal_type', ['BEN', 'BC', 'ULC', 'CC'])
def test_numbered_incorp_notification_future_effective(app, session, legal_type, mock_pdfs):
    """Assert that future-effective PAID IA with no legal name uses the numbered description as business_name."""
    # Create a filing where the business has no legal name (numbered company scenario)
    filing = _prep_numbered_incorp_filing(session, 'BC1234567', '1', legal_type)
    make_future_effective(filing)
    email = process_filing(filing, 'incorporationApplication', 'PAID')

    assert email is not None
    assert email['content']['body']
    # When legalName is absent from the DB business:
    # - falls back to numberedDescription as business_name in subject
    # - falls back to 'Not Available' in the tombstone
    numbered_description = Business.BUSINESSES[Business.LegalTypes(legal_type)]['numberedDescription']
    assert numbered_description in email['content']['subject']
    assert "Business Name: Not Available" not in email['content']['body']


@pytest.mark.parametrize('legal_type', ['BEN', 'BC', 'ULC', 'CC'])
def test_numbered_incorp_notification_completed(app, session, legal_type, mock_pdfs):
    """Assert that for a COMPLETED IA the business legalName is used in the subject."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', legal_type=legal_type)
    email = process_filing(filing, 'incorporationApplication', 'COMPLETED')

    assert email is not None
    assert email['content']['body']
    assert 'test business - Successful Incorporation' == email['content']['subject']


# ---------------------------------------------------------------------------
# test_maintenance_notification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(['status', 'filing_type', 'submitter_role'], [
    ('PAID', 'changeOfAddress', None),
    ('PAID', 'alteration', None),
    ('COMPLETED', 'annualReport', None),
    ('COMPLETED', 'changeOfAddress', None),
    ('COMPLETED', 'changeOfDirectors', None),
    ('COMPLETED', 'alteration', None),
    ('COMPLETED', 'alteration', 'staff')
])
def test_maintenance_notification(app, session, status, filing_type, submitter_role,
                                  mock_pdfs, mock_recipients, mock_user_email):
    """Assert that maintenance filings produce an email with the correct recipients and attachments."""
    # setup filing + business for email
    filing = prep_maintenance_filing(session, 'BC1234567', '1', status, filing_type, submitter_role=submitter_role)
    if status == 'PAID':
        make_future_effective(filing)
    token = 'token'
    # test processor
    email = process_filing(filing, filing_type, status)

    if filing_type == 'alteration':
        if submitter_role:
            assert f'{submitter_role}@email.com' in email['recipients']
        else:
            assert 'user@email.com' in email['recipients']

    assert 'test@test.com' in email['recipients']
    assert email['content']['body']
    assert email['content']['attachments'] == []
    assert mock_pdfs.call_args[0][0] == token
    assert mock_pdfs.call_args[0][1]['identifier'] == 'BC1234567'
    assert mock_pdfs.call_args[0][1]['legalType'] == Business.LegalTypes.BCOMP.value
    assert mock_pdfs.call_args[0][1]['legalName'] == 'test business'
    assert mock_pdfs.call_args[0][2] == filing
    assert mock_recipients.call_args[0][0] == status
    assert mock_recipients.call_args[0][1] == filing.filing_json
    assert mock_recipients.call_args[0][2] == token


def test_filing_attachments_ia_paid_future_effective(session, config):
    """IA PAID future-effective: filing PDF + receipt are attached."""
    filing = prep_incorp_filing(session, None, '1', 'PAID', 'BC')
    temp_reg_id = filing.temp_reg
    make_future_effective(filing)
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, temp_reg_id, filing,
                         {'incorporationApplication': b'pdf_content_1'}, receipt=b'pdf_content_2')
        output = process_filing(filing, 'incorporationApplication', 'PAID')

    assert output is not None
    attachments = output['content']['attachments']
    # IA always adds the filing application PDF + receipt.
    assert len(attachments) == 2
    assert_attachment(attachments[0], 'Incorporation Application.pdf', 'pdf_content_1', '1')
    assert_attachment(attachments[1], 'Receipt.pdf', 'pdf_content_2', '2')


def test_filing_attachments_ia_completed_bc(session, config):
    """IA COMPLETED BC: IncorporationApplication + Notice of Articles + Certificate of Incorporation + Receipt."""
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'BC')
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing, {
            'incorporationApplication': b'pdf_content_0',
            'noticeOfArticles': b'pdf_content_1',
            'certificateOfIncorporation': b'pdf_content_2',
        }, receipt=b'pdf_content_3')
        output = process_filing(filing, 'incorporationApplication', 'COMPLETED')

    attachments = output['content']['attachments']
    # IA COMPLETED BC: IncorporationApplication + NOA + Certificate + Receipt = 4 attachments
    assert len(attachments) == 4
    file_names = [a['fileName'] for a in attachments]
    assert 'Incorporation Application.pdf' in file_names
    assert 'Notice of Articles.pdf' in file_names
    # New _add_filing_document_pdf replaces " Of " -> " of " (lowercase "of")
    assert 'Certificate of Incorporation.pdf' in file_names
    assert 'Receipt.pdf' in file_names


def test_filing_attachments_ia_completed_coop(session, config):
    """IA COMPLETED COOP: IncorporationApplication + Certificate + Certified Rules + Memorandum + Receipt."""
    identifier = 'CP1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', 'CP')
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing, {
            'incorporationApplication': b'pdf_content_0',
            'certificateOfIncorporation': b'pdf_content_1',
            'certifiedRules': b'pdf_content_2',
            'certifiedMemorandum': b'pdf_content_3',
        }, receipt=b'pdf_content_4')
        output = process_filing(filing, 'incorporationApplication', 'COMPLETED')

    attachments = output['content']['attachments']
    # IA COMPLETED COOP: IncorporationApplication + Certificate + Rules + Memorandum + Receipt = 5 attachments
    assert len(attachments) == 5
    file_names = [a['fileName'] for a in attachments]
    assert 'Incorporation Application.pdf' in file_names
    # New _add_filing_document_pdf replaces " Of " -> " of " (lowercase "of")
    assert 'Certificate of Incorporation.pdf' in file_names
    assert 'Certified Rules.pdf' in file_names
    assert 'Certified Memorandum.pdf' in file_names
    assert 'Receipt.pdf' in file_names


def test_filing_attachments_change_of_address_paid(session, config, mock_recipients):
    """changeOfAddress PAID: filing PDF + receipt."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'PAID', 'changeOfAddress')
    make_future_effective(filing)
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing,
                         {'changeOfAddress': b'pdf_content_1'}, receipt=b'pdf_content_2')
        output = process_filing(filing, 'changeOfAddress', 'PAID')

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert_attachment(attachments[0], 'Address Change.pdf', 'pdf_content_1')
    assert_attachment(attachments[1], 'Receipt.pdf', 'pdf_content_2')


def test_filing_attachments_annual_report_completed(session, config, mock_recipients):
    """annualReport COMPLETED: filing PDF (prefixed with the AR year) + receipt."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'COMPLETED', 'annualReport')
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing,
                         {'annualReport': b'pdf_content_1'}, receipt=b'pdf_content_2')
        output = process_filing(filing, 'annualReport', 'COMPLETED')

    attachments = output['content']['attachments']
    # annualReport PAID: filing application PDF + receipt
    assert len(attachments) == 2
    # _add_filing_document_pdf prefixes the AR filing PDF with the annualReportDate year (2018-04-08 -> 2018)
    assert_attachment(attachments[0], '2018 Annual Report.pdf', 'pdf_content_1')
    assert_attachment(attachments[1], 'Receipt.pdf', 'pdf_content_2')


def test_filing_attachments_alteration_completed_name_change(session, config, mock_recipients, mock_user_email):
    """alteration COMPLETED (BC, with name change): NOA + Certificate of Name Change."""
    identifier = 'BC1234567'
    filing = prep_maintenance_filing(session, identifier, '1', 'COMPLETED', 'alteration')
    # force the name-change branch via meta_data
    filing._meta_data = {'alteration': {'toLegalName': 'new name'}}
    filing.save()
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing, {
            'alteration': b'pdf_content_1',
            'noticeOfArticles': b'pdf_content_2',
            'certificateOfNameChange': b'pdf_content_3',
        }, receipt=b'pdf_content_4')
        output = process_filing(filing, 'alteration', 'COMPLETED')

    attachments = output['content']['attachments']
    assert len(attachments) == 4
    assert_attachment(attachments[0], 'Alteration.pdf', 'pdf_content_1')
    assert_attachment(attachments[1], 'Notice of Articles.pdf', 'pdf_content_2')
    assert_attachment(attachments[2], 'Certificate of Name Change.pdf', 'pdf_content_3')
    assert_attachment(attachments[3], 'Receipt.pdf', 'pdf_content_4')


def test_ia_future_effective_paid_body_contains_tombstone_fields(app, session, mock_pdfs):
    """Assert that IA future-effective PAID body contains business name and incorporation number."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'PAID', 'BC')
    make_future_effective(filing)
    email = process_filing(filing, 'incorporationApplication', 'PAID')

    assert email is not None
    body = email['content']['body']
    # The future template includes business-tombstone.md which renders these labels
    assert 'Business Name:' in body
    assert 'Incorporation Number:' in body
    # The future template includes what-happens-next.md
    assert 'What happens next' in body
    # Subject uses the "Filed" format
    assert 'Incorporation Application Filed' in email['content']['subject']


def test_ia_completed_body_and_subject(app, session, mock_pdfs):
    """Assert that IA COMPLETED body uses non-future template and subject is Successful Incorporation."""
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'COMPLETED', 'BC')
    email = process_filing(filing, 'incorporationApplication', 'COMPLETED')

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
def test_business_number_rendering(app, session, legal_type, tax_id, expected, mock_pdfs):
    """Assert business number renders as expected."""
    identifier = f'{legal_type}1234567'

    filing = prep_incorp_filing(session, identifier, '1', 'COMPLETED', legal_type)
    business = Business.find_by_identifier(identifier)
    business.tax_id = tax_id
    business.save()

    email = process_filing(filing, 'incorporationApplication', 'COMPLETED')

    assert email is not None
    body = email['content']['body']
    if expected:
        assert f'**Business Number:** {expected}' in body
        if expected == 'Not Available':
            assert '## Business Number' in body
    else:
        assert '**Business Number:**' not in body
        assert '## Business Number' not in body


@pytest.mark.parametrize('legal_type', [
    ('CP'),
    ('BC'),
])
def test_future_attachments_list_in_ia_future_effective_paid(app, session, config, legal_type):
    """Assert that the future_attachments_list is used for COOP and non-COOP future-effective PAID IA."""
    filing = prep_incorp_filing(session, None, '1', 'PAID', legal_type)
    temp_reg_id = filing.temp_reg
    make_future_effective(filing)
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, temp_reg_id, filing,
                         {'incorporationApplication': b'pdf_content_1'}, receipt=b'pdf_content_2')
        email = process_filing(filing, 'incorporationApplication', 'PAID')

    assert email is not None
    attachments = email['content']['attachments']
    assert len(attachments) == 2
    assert_attachment(attachments[0], 'Incorporation Application.pdf', 'pdf_content_1')
    assert_attachment(attachments[1], 'Receipt.pdf', 'pdf_content_2')


@pytest.mark.parametrize(['filing_type', 'status', 'expected_header', 'expected_subject'], [
    (
        'alteration',
        'PAID',
        'Your alteration has been filed',
        'test business - Alteration Filed',
    ),
    (
        'changeOfAddress',
        'PAID',
        'Your address change has been filed',
        'test business - Address Change Filed',
    ),
    (
        'alteration',
        'COMPLETED',
        'You have successfully completed your alteration with the BC Business Registry',
        'test business - Successful Alteration',
    ),
    (
        'annualReport',
        'COMPLETED',
        'You have successfully completed your 2018 annual report with the BC Business Registry',
        'test business - Successful Annual Report',
    ),
    (
        'changeOfAddress',
        'COMPLETED',
        'You have successfully completed your address change with the BC Business Registry',
        'test business - Successful Address Change',
    ),
    (
        'changeOfDirectors',
        'COMPLETED',
        'You have successfully completed your director change with the BC Business Registry',
        'test business - Successful Director Change',
    ),
])
def test_maintenance_filing_fe_renders_body_and_subject(app, session, filing_type, status, expected_header,
                                                        expected_subject, mock_pdfs, mock_recipients, mock_user_email):
    """Assert alteration and address change future effective emails render the expected body and subject."""
    filing = prep_maintenance_filing(session, 'BC1234567', '1', status, filing_type)
    if status == 'PAID':
        make_future_effective(filing)
    filing.save()
    email = process_filing(filing, filing_type, status)

    assert email is not None
    body = email['content']['body']
    assert expected_header in body
    assert not ".html]]" in body
    assert not ".md]]" in body
    assert email['content']['subject'] == expected_subject


# ---------------------------------------------------------------------------
# FIRM registration / changeOfRegistration via filing_notification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(['status', 'filing_type', 'legal_type', 'submitter_role'], [
    ('COMPLETED', 'registration', Business.LegalTypes.SOLE_PROP.value, None),
    ('COMPLETED', 'registration', Business.LegalTypes.PARTNERSHIP.value, None),
    ('COMPLETED', 'changeOfRegistration', Business.LegalTypes.SOLE_PROP.value, None),
    ('COMPLETED', 'changeOfRegistration', Business.LegalTypes.SOLE_PROP.value, 'staff'),
    ('COMPLETED', 'changeOfRegistration', Business.LegalTypes.PARTNERSHIP.value, None),
])
def test_firm_filing_via_filing_notification(app, session, status, filing_type, legal_type, submitter_role,
                                             mock_pdfs, mock_user_email):
    """Assert that FIRM registration and changeOfRegistration produce correct emails via filing_notification."""
    legal_name = 'test business'
    if filing_type == 'registration':
        filing = prep_registration_filing(session, 'FM1234567', '1', status, legal_type, legal_name, firm_parties())
    else:
        filing = prep_change_of_registration_filing(
            session, 'FM1234567', '1', legal_type, legal_name, submitter_role, firm_parties())

    email = process_filing(filing, filing_type, status)

    assert email is not None
    body = email['content']['body']
    assert body
    assert email['content']['attachments'] == []
    # FIRM legal types pass number_description="Registration" to the template,
    # which renders as "Registration Number:" in business-tombstone.md.
    assert 'Registration Number:' in body
    assert '[[' not in body
    assert ']]' not in body
    assert '## Attachments' in body
    assert mock_pdfs.call_args[0][1]['identifier'] == 'FM1234567'
    assert mock_pdfs.call_args[0][2] == filing
    assert CONTACT_POINT in email['recipients']
    assert PARTY_EMAIL_1 in email['recipients']
    
    if filing_type == 'registration':
        assert '## About these documents' in body
        assert '## Business Number' in body
        assert not mock_user_email.called
        assert f'{submitter_role}@email.com' not in email['recipients']
        assert 'user@email.com' not in email['recipients']
        if legal_type == Business.LegalTypes.PARTNERSHIP.value:
            assert PARTY_EMAIL_2 in email['recipients']

    else:
        if submitter_role:
            assert f'{submitter_role}@email.com' in email['recipients']
        else:
            assert mock_user_email.called
            assert 'user@email.com' in email['recipients']


def test_filing_attachments_registration_completed(session, config, mock_recipients):
    """registration COMPLETED: Statement of Registration filing PDF + receipt."""
    identifier = 'FM1234567'
    filing = prep_registration_filing(
        session, identifier, '1', 'COMPLETED', Business.LegalTypes.SOLE_PROP.value, 'test business', firm_parties())
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing,
                         {'registration': b'pdf_content_1'}, receipt=b'pdf_content_2')
        output = process_filing(filing, 'registration', 'COMPLETED')

    attachments = output['content']['attachments']
    # registration COMPLETED: Statement of Registration + Receipt
    assert len(attachments) == 2
    # 'registration' is special-cased to the 'Statement of Registration' file name.
    assert_attachment(attachments[0], 'Statement of Registration.pdf', 'pdf_content_1', '1')
    assert_attachment(attachments[1], 'Receipt.pdf', 'pdf_content_2', '2')


def test_filing_attachments_change_of_registration_completed(session, config, mock_recipients, mock_user_email):
    """changeOfRegistration COMPLETED: filing PDF + amended registration statement + receipt."""
    identifier = 'FM1234567'
    filing = prep_change_of_registration_filing(
        session, identifier, '1', Business.LegalTypes.SOLE_PROP.value, 'test business', None, firm_parties())
    with requests_mock.Mocker() as m:
        mock_filing_docs(m, config, identifier, filing, {
            'changeOfRegistration': b'pdf_content_1',
            'amendedRegistrationStatement': b'pdf_content_2',
        }, receipt=b'pdf_content_3')
        output = process_filing(filing, 'changeOfRegistration', 'COMPLETED')

    attachments = output['content']['attachments']
    # changeOfRegistration COMPLETED: filing PDF + amendedRegistrationStatement (extraPdfTypes) + Receipt
    assert len(attachments) == 3
    assert_attachment(attachments[0], 'Change of Registration.pdf', 'pdf_content_1', '1')
    assert_attachment(attachments[1], 'Amended Registration Statement.pdf', 'pdf_content_2', '2')
    assert_attachment(attachments[2], 'Receipt.pdf', 'pdf_content_3', '3')


@pytest.mark.parametrize(['filing_type', 'expected_subject_suffix'], [
    ('registration', 'Successful Registration'),
    ('changeOfRegistration', 'Successful Change of Registration'),
])
def test_firm_filing_subject(app, session, filing_type, expected_subject_suffix,
                             mock_pdfs, mock_recipients, mock_user_email):
    """Assert that registration and changeOfRegistration subjects use the correct filing title."""
    legal_name = 'test business'
    legal_type = Business.LegalTypes.SOLE_PROP.value
    if filing_type == 'registration':
        filing = prep_registration_filing(session, 'FM1234567', '1', 'COMPLETED', legal_type, legal_name,
                                           firm_parties())
    else:
        filing = prep_change_of_registration_filing(
            session, 'FM1234567', '1', legal_type, legal_name, None, firm_parties())
    email = process_filing(filing, filing_type, 'COMPLETED')

    assert email is not None
    assert email['content']['subject'] == f'JANE A DOE - {expected_subject_suffix}'
