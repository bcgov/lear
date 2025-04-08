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
"""The Unit Tests for the mras email processor."""
from business_emailer.email_processors import mras_notification
from tests.unit import prep_amalgamation_filing, prep_continuation_in_filing, prep_incorp_filing


def test_incorporation_app_mras_notification(app, session):
    """Assert mras notification email for Incorporation application filing."""
    # setup filing + business for email
    filing = prep_incorp_filing(session, 'BC1234567', '1', 'mras')
    # run processor
    email = mras_notification.process(
        {'filingId': filing.id, 'type': 'incorporationApplication', 'option': 'mras'})
    # check email values
    assert email['recipients'] == 'test@test.com'
    assert email['content']['subject'] == 'BC Business Registry Partner Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []


def test_amalgamation_mras_notification(app, session):
    """Assert mras notification email for Amalgamation filing."""
    # setup filing + business for email
    filing = prep_amalgamation_filing(session, 'BC1234567', '1', 'mras', 'TED business')
    # run processor
    email = mras_notification.process(
        {'filingId': filing.id, 'type': 'amalgamationApplication', 'option': 'mras'})
    # check email values
    assert email['recipients'] == 'test@test.com'
    assert email['content']['subject'] == 'BC Business Registry Partner Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []


def test_continuation_mras_notification(app, session):
    """Assert mras notification email for Continuation In filing."""
    # setup filing + business for email
    filing = prep_continuation_in_filing(session, 'BC1234567', '1', 'mras')

    # run processor
    email = mras_notification.process(
        {'filingId': filing.id, 'type': 'continuationIn', 'option': 'mras'})
    # check email values
    assert email['recipients'] == 'test@test.com'
    assert email['content']['subject'] == 'BC Business Registry Partner Information'
    assert email['content']['body']
    assert email['content']['attachments'] == []
