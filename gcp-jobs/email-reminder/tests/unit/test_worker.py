# Copyright © 2024 Province of British Columbia
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
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from simple_cloudevent import from_queue_message

from business_model.models import Business, Filing
from email_reminder import flags
from email_reminder.services.flags import Flags
from email_reminder.worker import AccountService, gcp_queue, find_and_send_ar_reminder, get_ar_fee, get_businesses, run, send_email, send_outstanding_bcomps_ar_reminder

from . import factory_business


def assert_publish_mock(app: Flask, mock: MagicMock, business_id: str, ar_fee: str, ar_year: str):
    """Assert the publish mock was called with the expected values."""
    assert mock.call_args[0][0] == app.config['BUSINESS_EMAILER_TOPIC']
    assert mock.call_args[0][1]
    email_msg = from_queue_message(mock.call_args[0][1])
    assert email_msg.source == 'emailReminderJob'
    assert email_msg.subject == 'filing'
    assert email_msg.type == 'bc.registry.reminder.annualReport'
    assert email_msg.data.get('email', {}).get('businessId') == business_id
    assert email_msg.data.get('email', {}).get('arFee') == ar_fee
    assert email_msg.data.get('email', {}).get('arYear') == ar_year

def test_send_email(app: Flask):
    """Assert the send_email method works as expected."""
    business_id = '1234'
    ar_fee = '43.50'
    ar_year = '2025'
    with patch.object(gcp_queue, 'publish', return_value=None) as email_publish_mock:
        send_email(business_id, ar_fee, ar_year)
        email_publish_mock.assert_called()
        assert_publish_mock(app, email_publish_mock, business_id, ar_fee, ar_year)

@pytest.mark.parametrize('_test_name, founding_date, reminder_year, rest_expiry_date, state, expected',[
    ('active_new_business', datetime.now(UTC), None, None, Business.State.ACTIVE, False),
    ('active_year_old_business', datetime.now(UTC) - timedelta(days=365), None, None, Business.State.ACTIVE, True),
    ('active_year_old_business_with_reminder_year', datetime.now(UTC) - timedelta(days=365), datetime.now(UTC).year, None, Business.State.ACTIVE, False),
    ('active_2year_old_business_with_old_reminder_year', datetime.now(UTC) - timedelta(days=730), (datetime.now(UTC) - timedelta(days=730)).year, None, Business.State.ACTIVE, True),
    ('active_2year_old_business_with_reminder_year', datetime.now(UTC) - timedelta(days=730), (datetime.now(UTC) - timedelta(days=364)).year, None, Business.State.ACTIVE, False),
    ('active_year_old_business_with_restoration', datetime.now(UTC) - timedelta(days=365), None, datetime.now(UTC) + timedelta(days=10), Business.State.ACTIVE, False),
    ('historical_year_old_business', datetime.now(UTC) - timedelta(days=365), None, None, Business.State.HISTORICAL, False),
])
def test_get_businesses(app, session, _test_name, founding_date, reminder_year, rest_expiry_date, state, expected):
    """Assert the get_businesses method works as expected."""
    business = factory_business(identifier='BC1234567',
                                founding_date=founding_date,
                                last_ar_reminder_year=reminder_year,
                                restoration_expiry_date=rest_expiry_date,
                                state=state)
    resp = get_businesses([business.legal_type])
    if expected:
        assert len(resp.items) == 1
        assert resp.items[0].id == business.id
    else:
        assert len(resp.items) == 0

@pytest.mark.parametrize('_test_name, ld_flag_value, legal_type, last_reminder_year, expected',[
    ('BEN_flag_off', False, Business.LegalTypes.BCOMP.value, 2023, True),
    ('BEN_flag_on', True, Business.LegalTypes.BCOMP.value, 2023, True),
    ('BC_flag_off', False, Business.LegalTypes.COMP.value, 2023, False),
    ('BC_flag_on', True, Business.LegalTypes.COMP.value, 2023, True),
])
def test_find_and_send_ar_reminder(ld, app, session, _test_name, ld_flag_value, legal_type, last_reminder_year, expected):
    """Assert the find_and_send_ar_reminder method works as expected."""
    ld.update(ld.flag('enable-bc-ccc-ulc-email-reminder').variation_for_all(ld_flag_value))
    flags.init_app(app, ld)
    
    business = factory_business(identifier='BC1234567',
                                entity_type=legal_type,
                                last_ar_reminder_year=last_reminder_year)
    test_fee = '43.50'
    with patch.object(AccountService, 'get_bearer_token', return_value='token'),\
        patch.object(gcp_queue, 'publish', return_value=None) as publish_mock,\
            patch("email_reminder.worker.get_ar_fee", return_value=test_fee):
                find_and_send_ar_reminder()
                if not expected:
                    publish_mock.assert_not_called()
                else:
                    publish_mock.assert_called()
                    ar_year = str((last_reminder_year or business.founding_date.year) + 1)
                    assert_publish_mock(app, publish_mock, business.id, test_fee, ar_year)
            
    
@pytest.mark.parametrize('_test_name, legal_type, last_ar_year, expected',[
    ('BEN_publish', Business.LegalTypes.BCOMP.value, 2023, True),
    ('BEN_no_ar_publish', Business.LegalTypes.BCOMP.value, None, True),
    ('BEN_no_publish', Business.LegalTypes.BCOMP.value, datetime.now(UTC).year, False),
    ('BC_no_publish', Business.LegalTypes.COMP.value, 2023, False),
])
def test_send_outstanding_bcomps_ar_reminder(app, session, _test_name, legal_type, last_ar_year, expected):
    """Assert the send_outstanding_bcomps_ar_reminder method works as expected."""
    ar_date = datetime(year=last_ar_year, month=1, day=1, tzinfo=UTC) if last_ar_year else None
    business = factory_business(identifier='BC1234567',
                                entity_type=legal_type,
                                last_ar_date=ar_date)
    test_fee = '43.50'
    with patch.object(AccountService, 'get_bearer_token', return_value='token'),\
        patch.object(gcp_queue, 'publish', return_value=None) as publish_mock,\
            patch("email_reminder.worker.get_ar_fee", return_value=test_fee):
                send_outstanding_bcomps_ar_reminder()
                if not expected:
                    publish_mock.assert_not_called()
                else:
                    publish_mock.assert_called()
                    ar_year = str((last_ar_year or business.founding_date.year) + 1)
                    assert_publish_mock(app, publish_mock, business.id, test_fee, ar_year)

@pytest.mark.parametrize('_test_name, config_value, expected',[
    ('run_find_and_send_ar_reminder', None, 'find_and_send_ar_reminder'),
    ('run_send_outstanding_bcomps_ar_reminder', 'send.outstanding.bcomps', 'send_outstanding_bcomps_ar_reminder'),
])
def test_run(app, _test_name, config_value, expected):
    """Assert the run method works as expected."""
    with patch("email_reminder.worker.find_and_send_ar_reminder", return_value=None) as mock_1,\
        patch("email_reminder.worker.send_outstanding_bcomps_ar_reminder", return_value=None) as mock_2:
            app.config['SEND_OUTSTANDING_BCOMPS'] = config_value
            run()
            if expected == 'find_and_send_ar_reminder':
                mock_1.assert_called()
            else:
                mock_2.assert_called()