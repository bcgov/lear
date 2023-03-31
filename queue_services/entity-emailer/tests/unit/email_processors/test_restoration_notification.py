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
"""The Unit Tests for the Restoration email processor."""

from unittest.mock import patch

import responses

from entity_emailer.email_processors import restoration_notification
from tests.unit import prep_restoration_filing


@responses.activate
def test_complete_full_restoration_notification_includes_notice_of_articles_and_incorporation_cert(session, config):
    """Test completed full restoration notification."""
    # setup filing + business for email
    status = 'COMPLETED'
    legal_name = 'test business'
    business_id = 'BC1234567'
    token = 'token'
    filing = prep_restoration_filing(session, business_id, '1', status, 'BC', legal_name)
    responses.add(
        responses.GET,
        f'{config.get("LEGAL_API_URL")}/businesses/{business_id}/filings/{filing.id}?type=noticeOfArticles',
        status=200
    )
    responses.add(
        responses.GET,
        f'{config.get("LEGAL_API_URL")}/businesses/{business_id}/filings/{filing.id}?type=certificate',
        status=200
    )
    restoration_notification.process({
        'filingId': filing.id,
        'type': 'restoration',
        'option': status
    }, token)
    assert len(responses.calls) == 2


@responses.activate
def test_paid_restoration_notification_includes_receipt_and_restoration_application_attachments(session, config):
    """Test PAID full restoration notification."""
    # setup filing + business for email
    legal_name = 'test business'
    business_id = 'BC1234567'
    status = 'PAID'
    filing = prep_restoration_filing(session, business_id, '1', status, 'BC', legal_name)
    token = 'token'
    responses.add(
        responses.POST,
        f'{config.get("PAY_API_URL")}/{filing.payment_token}/receipts',
        status=200
    )
    responses.add(
        responses.GET,
        f'{config.get("LEGAL_API_URL")}/businesses/{business_id}/filings/{filing.id}',
        status=200
    )
    restoration_notification.process({
        'filingId': filing.id,
        'type': 'restoration',
        'option': status
    }, token)
    assert len(responses.calls) == 2


def test_completed_full_restoration_notification(session, config):
    """Test completed full restoration notification."""
    # setup filing + business for email
    status = 'COMPLETED'
    legal_name = 'test business'
    business_id = 'BC1234567'
    filing = prep_restoration_filing(session, business_id, '1', status, 'BC', legal_name)
    token = 'token'
    # test processor
    email_dict = restoration_notification.process({
        'filingId': filing.id,
        'type': 'restoration',
        'option': status
    }, token)
    email = email_dict['content']['body']
    assert email_dict['content']['subject'] == 'test business - Restoration Documents from the Business Registry'
    assert 'joe@email.com' in email_dict['recipients']
    assert 'You have successfully restored your business with the BC Business Registry' in email


def test_completed_extended_restoration_notification(session):
    """Test completed extended restoration notification includes specific wording."""
    # setup filing + business for email
    status = 'COMPLETED'
    legal_name = 'test business'
    filing = prep_restoration_filing(session, 'BC1234567', '1', status, 'BC', legal_name, 'limitedRestorationExtension')
    token = 'token'
    # test processor
    email_dict = restoration_notification.process({
        'filingId': filing.id,
        'type': 'restoration',
        'option': status
    }, token)
    email = email_dict['content']['body']
    assert 'You have successfully extended the period of restoration with the BC Business' in email


@responses.activate
def test_paid_restoration_notification(session):
    """Test PAID full restoration notification."""
    # setup filing + business for email
    legal_name = 'test business'
    status = 'PAID'
    filing = prep_restoration_filing(session, 'BC1234567', '1', status, 'BC', legal_name)
    token = 'token'
    # test processor
    with patch.object(restoration_notification, '_get_pdfs', return_value=[]):
        email_dict = restoration_notification.process({
            'filingId': filing.id,
            'type': 'restoration',
            'option': status
        }, token)
        email = email_dict['content']['body']
        assert 'joe@email.com' in email_dict['recipients']
        assert email_dict['content']['subject'] == 'test business - Confirmation of Filing from the Business Registry'
        assert 'joe@email.com' in email_dict['recipients']
        assert 'You have successfully filed your restoration with the BC Business Registry' in email
        assert email_dict['content']['attachments'] == []
