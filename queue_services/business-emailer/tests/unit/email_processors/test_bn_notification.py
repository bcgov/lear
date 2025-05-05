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
"""The Unit Tests for business number email processor."""
from unittest.mock import patch

from business_model.models import Business

from business_emailer.email_processors import bn_notification
from tests.unit import (
    prep_amalgamation_filing,
    prep_continuation_in_filing,
    prep_incorp_filing,
    prep_registration_filing,
)


def test_incorporation_bn_notificaton(app, session):
    """Assert that the bn email processor builds the email correctly."""
    # setup filing + business for email
    identifier = 'BC1234567'
    filing = prep_incorp_filing(session, identifier, '1', 'bn')
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id
    # run processor
    email = bn_notification.process(
        {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': 'BC1234567'})
    # check email values
    assert 'comp_party@email.com' in email['recipients']
    assert 'test@test.com' in email['recipients']
    assert email['content']['subject'] == f'{business.legal_name} - Business Number Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []


def test_amalgamation_bn_notificaton(app, session):
    """Assert bn notification email for Amalgamation filing."""
    # setup filing + business for email
    identifier = 'BC1234567'
    filing = prep_amalgamation_filing(session, identifier, '1', 'bn', 'TED business')
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id
    # run processor
    email = bn_notification.process(
        {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': 'BC1234567'})
    # check email values
    assert 'comp_party@email.com' in email['recipients']
    assert 'test@test.com' in email['recipients']
    assert email['content']['subject'] == f'{business.legal_name} - Business Number Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []


def test_continuation_bn_notificaton(mocker, app, session):
    """Assert bn notification email for Continuation filing."""
    # setup filing + business for email
    identifier = 'BC1234567'
    filing = prep_continuation_in_filing(session, identifier, '1', 'bn')
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id
    # run processor
    email = bn_notification.process(
        {'filingId': None, 'type': 'businessNumber', 'option': 'bn', 'identifier': 'BC1234567'})
    # check email values
    assert 'comp_party@email.com' in email['recipients']
    assert 'test@test.com' in email['recipients']
    assert email['content']['subject'] == f'{business.legal_name} - Business Number Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []


def test_bn_move_notificaton(app, session):
    """Assert that the bn move email processor builds the email correctly."""
    # setup filing + business for email
    identifier = 'FM1234567'
    filing = prep_registration_filing(session, identifier, '1', 'COMPLETED',
                                      Business.LegalTypes.SOLE_PROP.value, 'test business')
    token = 'token'
    business = Business.find_by_identifier(identifier)
    # sanity check
    assert filing.id
    assert business.id

    # run processor
    with patch.object(bn_notification, 'get_recipient_from_auth', return_value='user@email.com'):
        email = bn_notification.process_bn_move({'identifier': identifier, 'oldBn': '993775204BC0001', 'newBn': '993777399BC0001'},
                                                token)
        # check email values
        assert 'user@email.com' in email['recipients']
        assert email['content']['subject'] == f'{business.legal_name} - Business Number Changed'
        assert email['content']['body']
        assert email['content']['attachments'] == []
