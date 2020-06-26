# Copyright © 2019 Province of British Columbia
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
"""The Test Suites to ensure that the worker is operating correctly."""
from unittest.mock import patch

import pytest
from legal_api.models import Business
from legal_api.services.bootstrap import AccountService

from entity_emailer import worker
from entity_emailer.email_processors import incorp_notification
from tests.unit import email_prepped_filing


def test_process_filing_missing_app(app, session):
    """Assert that an email will fail with no flask app supplied."""
    # setup
    email_msg = {'email': {'type': 'bn'}}

    # TEST
    with pytest.raises(Exception):
        worker.process_email(email_msg, flask_app=None)


@pytest.mark.parametrize('option', [
    ('filed'),
    ('registered'),
])
def test_process_incorp_email(app, session, option):
    """Assert that an INCORP email msg is processed correctly."""
    # setup filing + business for email
    filing = email_prepped_filing(session, 'BC1234567', '1', option)
    token = '1'
    # test worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(incorp_notification, '_get_pdfs', return_value=[]) as mock_get_pdfs:
            with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
                worker.process_email(
                    {'email': {'filingId': filing.id, 'type': 'incorporationApplication', 'option': option}}, app)

                assert mock_get_pdfs.call_args[0][0] == option
                assert mock_get_pdfs.call_args[0][1] == token
                assert mock_get_pdfs.call_args[0][2] == {'identifier': 'BC1234567'}
                assert mock_get_pdfs.call_args[0][3] == filing

                if option == 'filed':
                    assert 'comp_party@email.com' in mock_send_email.call_args[0][0]['recipients']
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                        'Confirmation of Filing from the Business Registry'
                else:
                    assert mock_send_email.call_args[0][0]['content']['subject'] == \
                        'Incorporation Documents from the Business Registry'
                assert 'test@test.com' in mock_send_email.call_args[0][0]['recipients']
                assert mock_send_email.call_args[0][0]['content']['body']
                assert mock_send_email.call_args[0][0]['content']['attachments'] == []
                assert mock_send_email.call_args[0][1] == token


def test_process_mras_email(app, session):
    """Assert that an MRAS email msg is processed correctly."""
    # setup filing + business for email
    filing = email_prepped_filing(session, 'BC1234567', '1', 'mras')
    token = '1'
    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
            worker.process_email(
                {'email': {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'mras'}}, app)

            # check vals
            assert mock_send_email.call_args[0][0]['content']['subject'] == 'BC Business Registry Partner Information'
            assert mock_send_email.call_args[0][0]['recipients'] == 'test@test.com'
            assert mock_send_email.call_args[0][0]['content']['body']
            assert mock_send_email.call_args[0][0]['content']['attachments'] == []
            assert mock_send_email.call_args[0][1] == token


def test_process_bn_email(app, session):
    """Assert that a BN email msg is processed correctly."""
    # setup filing + business for email
    identifier = 'BC1234567'
    filing = email_prepped_filing(session, identifier, '1', 'bn')
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id
    token = '1'
    # run worker
    with patch.object(AccountService, 'get_bearer_token', return_value=token):
        with patch.object(worker, 'send_email', return_value='success') as mock_send_email:
            worker.process_email(
                {'email': {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': 'BC1234567'}},
                app
            )
            # check email values
            assert 'comp_party@email.com' in mock_send_email.call_args[0][0]['recipients']
            assert 'test@test.com' in mock_send_email.call_args[0][0]['recipients']
            assert mock_send_email.call_args[0][0]['content']['subject'] == \
                f'{business.legal_name} - Business Number Information'
            assert mock_send_email.call_args[0][0]['content']['body']
            assert mock_send_email.call_args[0][0]['content']['attachments'] == []
