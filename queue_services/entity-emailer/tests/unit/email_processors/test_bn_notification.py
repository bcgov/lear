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
from legal_api.models import Business

from entity_emailer.email_processors import bn_notification
from tests.unit import prep_incorp_filing


def test_bn_notificaton(app, session):
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
