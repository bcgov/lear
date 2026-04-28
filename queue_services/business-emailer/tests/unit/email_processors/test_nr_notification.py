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


_is_modernized = nr_notification.__is_modernized
_is_colin = nr_notification.__is_colin
_get_instruction_group = nr_notification.__get_instruction_group


@pytest.mark.parametrize('legal_type,expected', [
    ('GP', True), ('DBA', True), ('FR', True), ('CP', True), ('BC', True),
    ('CR', False), ('SO', False), ('XSO', False), ('', False), ('bc', False), (None, False),
])
def test_is_modernized(legal_type, expected):
    """Assert __is_modernized matches only the modernized legal types (case-sensitive)."""
    assert _is_modernized(legal_type) is expected


@pytest.mark.parametrize('legal_type,expected', [
    ('CR', True), ('UL', True), ('CC', True), ('XCR', True), ('XUL', True), ('RLC', True),
    ('BC', False), ('SO', False), ('GP', False), ('', False), ('cr', False), (None, False),
])
def test_is_colin(legal_type, expected):
    """Assert __is_colin matches only the colin legal types (case-sensitive)."""
    assert _is_colin(legal_type) is expected


@pytest.mark.parametrize('legal_type,expected', [
    ('SO', True), ('XSO', True),
    ('BC', False), ('CR', False), ('GP', False), ('', False), ('so', False), (None, False),
])
def test_is_society(legal_type, expected):
    """Assert _is_society matches only the society legal types (case-sensitive)."""
    assert nr_notification._is_society(legal_type) is expected


@pytest.mark.parametrize('legal_type,expected', [
    ('GP', 'modernized'), ('DBA', 'modernized'), ('FR', 'modernized'),
    ('CP', 'modernized'), ('BC', 'modernized'),
    ('CR', 'colin'), ('UL', 'colin'), ('CC', 'colin'),
    ('XCR', 'colin'), ('XUL', 'colin'), ('RLC', 'colin'),
    ('SO', 'so'), ('XSO', 'so'),
    ('', ''), ('unknown', ''), (None, ''),
])
def test_get_instruction_group(legal_type, expected):
    """Assert __get_instruction_group returns the correct group or empty string."""
    assert _get_instruction_group(legal_type) == expected


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


@pytest.mark.parametrize('entity_type_cd', [
    'BC',       # __is_modernized branch → NR-BEFORE-EXPIRY-MODERNIZED.html
    'CR',       # __is_colin branch       → NR-BEFORE-EXPIRY-COLIN.html
    'SO',       # _is_society branch      → NR-BEFORE-EXPIRY-SO.html
    'UNKNOWN',  # falls through to the default NR-BEFORE-EXPIRY.html
])
def test_nr_notification_before_expiry_entity_type(app, session, entity_type_cd):
    """Assert BEFORE_EXPIRY picks the group-specific template when entity_type_cd is present."""
    nr_number = 'NR 1234567'
    nr_json = {
        'expirationDate': '2021-07-20T00:00:00+00:00',
        'names': [{'name': 'TEST COMP', 'state': 'APPROVED'}],
        'legalType': 'BC',
        'entity_type_cd': entity_type_cd,
        'applicants': {'emailAddress': 'test@test.com'}
    }

    with patch.object(NameXService, 'query_nr_number', return_value=MockResponse(nr_json, 200)):
        email = nr_notification.process({
            'identifier': nr_number,
            'request': {'nrNum': nr_number, 'option': 'before-expiry'}
        }, 'before-expiry')

    assert email['content']['subject'] == f'{nr_number} - Expiring Soon'
    assert email['content']['body']
    assert nr_number in email['content']['body']
    assert 'TEST COMP' in email['content']['body']
