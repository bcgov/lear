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

from entity_emailer.email_processors import restoration_notification
from tests.unit import prep_restoration_filing


def test_completed_full_restoration_notification(app, session):
    # setup filing + business for email
    status = "COMPLETED"
    legal_name = 'test business'
    filing = prep_restoration_filing(session, 'BC1234567', '1', status, 'BC', legal_name)
    token = 'token'
    # test processor
    with patch.object(restoration_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email_dict = restoration_notification.process({
            'filingId': filing.id,
            'type': 'restoration',
            'option': status
        }, token)
        email = email_dict['content']['body']
        assert email_dict['content']['subject'] == 'test business - Restoration Documents from the Business Registry'
        assert 'joe@email.com' in email_dict['recipients']
        assert 'You have successfully restored your business with the BC Business Registry' in email
        assert email_dict['content']['attachments'] == []
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
        assert mock_get_pdfs.call_args[0][2]['legalType'] == 'BC'
        assert mock_get_pdfs.call_args[0][3] == filing


def test_completed_extended_restoration_notification(app, session):
    # setup filing + business for email
    status = "COMPLETED"
    legal_name = 'test business'
    filing = prep_restoration_filing(session, 'BC1234567', '1', status, 'BC', legal_name, 'limitedRestorationExtension')
    token = 'token'
    # test processor
    with patch.object(restoration_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
        email_dict = restoration_notification.process({
            'filingId': filing.id,
            'type': 'restoration',
            'option': status
        }, token)
        email = email_dict['content']['body']
        assert 'You have successfully extended the period of restoration with the BC Business' in email
        

def test_paid_restoration_notification(app, session):
    # setup filing + business for email
    legal_name = 'test business'
    status = "PAID"
    filing = prep_restoration_filing(session, 'BC1234567', '1', status, 'BC', legal_name)
    token = 'token'
    # test processor
    with patch.object(restoration_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
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
        assert mock_get_pdfs.call_args[0][0] == status
        assert mock_get_pdfs.call_args[0][1] == token
        assert mock_get_pdfs.call_args[0][2]['identifier'] == 'BC1234567'
        assert mock_get_pdfs.call_args[0][2]['legalType'] == 'BC'
        assert mock_get_pdfs.call_args[0][3] == filing
