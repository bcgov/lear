# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""The Unit Tests for the Appoint Receiver email processor."""
import base64
from unittest.mock import patch

import pytest
import requests_mock
from business_model.models import Business

from business_emailer.email_processors import appoint_receiver_notification
from tests.unit import prep_appoint_receiver_filing


@pytest.mark.parametrize('status,legal_name,is_numbered', [
    ('COMPLETED', 'test business', False),
    ('COMPLETED', 'BC1234567', True),
])
def test_appoint_receiver_notification(app, session, status, legal_name, is_numbered):
    """Assert that the appoint_receiver email processor builds the expected email."""
    # setup filing + business for email
    filing = prep_appoint_receiver_filing(
        session, 'BC1234567', '1', Business.LegalTypes.COMP.value, legal_name)
    token = 'token'
    # test processor
    with patch.object(appoint_receiver_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        with patch.object(appoint_receiver_notification, 'get_recipient_from_auth',
                          return_value='recipient@email.com'):
            email = appoint_receiver_notification.process(
                {'filingId': filing.id, 'type': 'appointReceiver', 'option': status}, token)

            if is_numbered:
                assert email['content']['subject'] == 'Numbered Company - Receiver appointed'
            else:
                assert email['content']['subject'] == f'{legal_name} - Receiver appointed'

            assert email['recipients'] == 'recipient@email.com'
            assert email['requestBy'] == 'BCRegistries@gov.bc.ca'
            assert email['content']['body']
            assert email['content']['attachments'] == []

            assert mock_get_pdfs.call_args[0][0] == token
            assert mock_get_pdfs.call_args[0][1]['identifier'] == 'BC1234567'
            assert mock_get_pdfs.call_args[0][1]['legalName'] == legal_name
            assert mock_get_pdfs.call_args[0][1]['legalType'] == Business.LegalTypes.COMP.value
            assert mock_get_pdfs.call_args[0][2] == filing


def test_appoint_receiver_attachments(session, config):
    """Assert _get_pdfs assembles the Appoint Receiver filing PDF and receipt."""
    identifier = 'BC1234567'
    filing = prep_appoint_receiver_filing(
        session, identifier, '1', Business.LegalTypes.COMP.value, 'test business')
    token = 'token'
    with patch.object(appoint_receiver_notification, 'get_recipient_from_auth',
                      return_value='recipient@email.com'):
        with requests_mock.Mocker() as m:
            m.get(
                f'{config.get("LEGAL_API_URL")}/businesses/{identifier}'
                f'/filings/{filing.id}/documents/appointReceiver',
                content=b'pdf_content_1',
                status_code=200,
            )
            m.post(
                f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
                content=b'pdf_content_2',
                status_code=201,
            )
            output = appoint_receiver_notification.process(
                {'filingId': filing.id, 'type': 'appointReceiver', 'option': 'COMPLETED'}, token)

    attachments = output['content']['attachments']
    assert len(attachments) == 2
    assert attachments[0]['fileName'] == 'Appoint Receiver.pdf'
    assert base64.b64decode(attachments[0]['fileBytes']).decode('utf-8') == 'pdf_content_1'
    assert attachments[1]['fileName'] == 'Receipt.pdf'
    assert base64.b64decode(attachments[1]['fileBytes']).decode('utf-8') == 'pdf_content_2'
