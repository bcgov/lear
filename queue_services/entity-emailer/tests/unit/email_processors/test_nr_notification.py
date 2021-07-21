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
"""The Unit Tests for the name request expiry email processor."""
from unittest.mock import patch

import pytest
from legal_api.services import NameXService

from entity_emailer.email_processors import nr_notification
from tests import MockResponse


@pytest.mark.parametrize(['option', 'nr_number', 'subject', 'expiration_date'], [
    ('before-expiry', 'NR 1234567', 'Expiring Soon', None),
    ('expired', 'NR 1234567', 'Expired', None),
    ('renewal', 'NR 1234567', 'Confirmation of Renewal', '2021-07-20T00:00:00+00:00'),
    ('upgrade', 'NR 1234567', 'Confirmation of Upgrade', None)
])
def test_nr_notification(app, session, option, nr_number, subject, expiration_date):
    """Assert that the nr notification can be processed."""
    nr_json = {
        'expirationDate': expiration_date,
        'applicants': {
            'emailAddress': 'test@test.com'
        }
    }
    nr_response = MockResponse(nr_json, 200)

    # test processor
    with patch.object(NameXService, 'query_nr_number', return_value=nr_response) \
            as mock_query_nr_number:
        email = nr_notification.process(
            {
                'nrNumber': nr_number,
                'type': 'namerequest',
                'option': option,
                'submitCount': 1
            }, option)
        assert email['content']['subject'] == f'{nr_number} - {subject}'

        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_query_nr_number.call_args[0][0] == nr_number
