# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure the Annual Report is validated correctly."""
import copy
from datetime import date
from http import HTTPStatus

import pytest
from hypothesis import given
from hypothesis.strategies import dates, just, text
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Business
from legal_api.services.filings.validations.annual_report import validate_agm_year


@pytest.mark.parametrize(
    'test_name, now, ar_date, agm_date, last_agm_date, submission_date, expected_code, expected_msg',
    [
        ('AGM_DATE_REQUIRED_IF_IN_FILING_YR',
         date(2018, 8, 5), date(2018, 8, 5), None, date(2017, 7, 1), date(2018, 9, 17),
         HTTPStatus.BAD_REQUEST,
         [{'error': 'Annual General MeetingDate must be a valid date when submitting '
           'an Annual Report in the current year.',
           'path': 'filing/annualReport/annualGeneralMeetingDate'}]),
        ('AGM_DATE_MISSING_FIRST_YEAR_WARNING',
         date(2019, 9, 17), date(2018, 8, 5), None, date(2017, 7, 1), date(2019, 9, 17),
         HTTPStatus.OK,
         [{'warning': 'Annual General Meeting Date (AGM) is being skipped. '
           'If another AGM is skipped, the business will be dissolved.',
           'path': 'filing/annualReport/annualGeneralMeetingDate'}]),
        ('AGM_DATE_MISSING_SECOND_YEAR_WARNING',
         date(2019, 9, 17), date(2018, 8, 5), None, date(2016, 7, 1), date(2019, 9, 17),
         HTTPStatus.OK,
         [{'warning': 'Annual General Meeting Date (AGM) is being skipped. '
           'The business will be dissolved, unless an extension and an AGM are held.',
           'path': 'filing/annualReport/annualGeneralMeetingDate'}]),
        ('AGM_DATE_NOT BEFORE_GO_LIVE_DATE_2019-08-12',
         date(2019, 9, 17), date(2019, 8, 5), date(2019, 8, 5), date(2017, 7, 1), date(2019, 9, 17),
         HTTPStatus.BAD_REQUEST,
         [{'error': 'Annual General Meeting Date is before 2019-08-12, so it must be submitted as a paper-filing.',
           'path': 'filing/annualReport/annualGeneralMeetingDate'}]),
    ])
def test_valid_agm_date(app, test_name, now, ar_date, agm_date, last_agm_date, submission_date,
                        expected_code, expected_msg):
    """Assert that the AGM date handles the examples that describe the AGM rules."""
    # with freeze_time(now):
    check_valid_agm_date(app, test_name, ar_date, agm_date, last_agm_date, submission_date, expected_code, expected_msg)


@given(test_name=text(), ar_date=dates(), agm_date=dates(), last_agm_date=dates(), submission_date=dates(),
       expected_code=just(400), expected_msg=just(None))
def test_valid_agm_date_hypothesis(app, test_name, ar_date, agm_date, last_agm_date, submission_date,
                                   expected_code, expected_msg):
    """Assert that the fuzzed parameters do not cause unhandled errors."""
    check_valid_agm_date(app, test_name, ar_date, agm_date, last_agm_date, submission_date, expected_code, expected_msg)


def check_valid_agm_date(app, test_name, ar_date, agm_date, last_agm_date, submission_date,
                         expected_code, expected_msg):
    """Assert that the AGM date for the filing is valid, or that valid warnings are returned."""
    # setup
    identifier = 'CP1234567'
    business = Business(identifier=identifier)
    business.last_agm_date = last_agm_date

    current_ar = copy.deepcopy(ANNUAL_REPORT)
    current_ar['filing']['business']['identifier'] = identifier
    current_ar['filing']['header']['date'] = submission_date.isoformat()
    current_ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    if agm_date:
        current_ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()
    else:
        current_ar['filing']['annualReport']['annualGeneralMeetingDate'] = None

    # Test it
    with app.app_context():
        err = validate_agm_year(business=business,
                                annual_report=current_ar)
    # Validate the outcome
    if expected_msg:  # examples check
        assert err.msg == expected_msg
        assert err.code == expected_code
    else:  # fuzzer check
        assert err is None or err.code == HTTPStatus.BAD_REQUEST
