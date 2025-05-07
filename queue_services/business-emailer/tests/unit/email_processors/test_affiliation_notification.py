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
"""The Unit Tests for the Affiliation email processor."""
from unittest.mock import patch

from business_emailer.email_processors import affiliation_notification
from tests.unit import prep_alteration_filing


def test_notifications(app, session):
    """Assert Affiliation notification is created."""
    subject = 'How to use BCRegistry.ca'
    company_name = 'Company Name'
    testing_email = 'test@test.com'
    token = 'token'
    filing = prep_alteration_filing(session, 'BC1234567', 'DRAFT', company_name)

    # test processor
    with patch.object(affiliation_notification, 'get_recipients', return_value=testing_email):
        email = affiliation_notification.process(
            {
                'filing': {
                    'header': {'filingId': filing.id}
                }
            },
            token
        )

        assert email['content']['subject'] == company_name + ' - ' + subject

        assert testing_email in email['recipients']
        assert email['content']['body']
