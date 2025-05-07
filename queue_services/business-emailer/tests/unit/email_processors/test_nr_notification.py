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
from datetime import datetime
from unittest.mock import patch

import pytest
from business_emailer.services.namex import NameXService
from business_model.utils.legislation_datetime import LegislationDatetime

from business_emailer.email_processors import nr_notification
from tests import MockResponse


default_legal_name = 'TEST COMP'
default_names_array = [{'name': default_legal_name, 'state': 'NE'}]


@pytest.mark.parametrize(['option', 'nr_number', 'subject', 'expiration_date', 'refund_value',
                         'expected_legal_name', 'names'], [
    ('before-expiry', 'NR 1234567', 'Expiring Soon', '2021-07-20T00:00:00+00:00', None, 'TEST2 Company Name',
        [{'name': 'TEST Company Name', 'state': 'NE'}, {'name': 'TEST2 Company Name', 'state': 'APPROVED'}]),
    ('before-expiry', 'NR 1234567', 'Expiring Soon', '2021-07-20T00:00:00+00:00', None, 'TEST3 Company Name',
        [{'name': 'TEST3 Company Name', 'state': 'CONDITION'}, {'name': 'TEST4 Company Name', 'state': 'NE'}]),
    ('expired', 'NR 1234567', 'Expired', None, None, 'TEST4 Company Name',
        [{'name': 'TEST5 Company Name', 'state': 'NE'}, {'name': 'TEST4 Company Name', 'state': 'APPROVED'}]),
    ('renewal', 'NR 1234567', 'Confirmation of Renewal', '2021-07-20T00:00:00+00:00', None, None, default_names_array),
    ('upgrade', 'NR 1234567', 'Confirmation of Upgrade', None, None, None, default_names_array),
    ('refund', 'NR 1234567', 'Refund request confirmation', None, '123.45', None, default_names_array)
])
def test_nr_notification(app, session, option, nr_number, subject, expiration_date, refund_value,
                         expected_legal_name, names):
    """Assert that the nr notification can be processed."""
    nr_json = {
        'expirationDate': expiration_date,
        'names': names,
        'legalType': 'BC',
        'applicants': {
            'emailAddress': 'test@test.com'
        }
    }
    nr_response = MockResponse(nr_json, 200)

    # test processor
    with patch.object(NameXService, 'query_nr_number', return_value=nr_response) \
            as mock_query_nr_number:
        email = nr_notification.process({
            'identifier': nr_number,
            'request': {
                'nrNum': nr_number,
                'option': option,
                'refundValue': refund_value
            }
        }, option)

        assert email['content']['subject'] == f'{nr_number} - {subject}'

        assert 'test@test.com' in email['recipients']
        assert email['content']['body']
        if option == nr_notification.Option.REFUND.value:
            assert f'${refund_value} CAD' in email['content']['body']
        assert email['content']['attachments'] == []
        assert mock_query_nr_number.call_args[0][0] == nr_number

        if option == nr_notification.Option.BEFORE_EXPIRY.value:
            assert nr_number in email['content']['body']
            assert expected_legal_name in email['content']['body']
            exp_date = datetime.fromisoformat(expiration_date)
            exp_date_tz = LegislationDatetime.as_legislation_timezone(exp_date)
            assert_expiration_date = LegislationDatetime.format_as_report_string(exp_date_tz)
            assert assert_expiration_date in email['content']['body']

        if option == nr_notification.Option.EXPIRED.value:
            assert nr_number in email['content']['body']
            assert expected_legal_name in email['content']['body']
