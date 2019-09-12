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
"""Test annual report year is managed correctly."""
import copy
from datetime import datetime
from http import HTTPStatus

import datedelta
import pytest
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.models import Business
from legal_api.services.filings.validations.annual_report import validate_ar_year


@pytest.mark.parametrize('test_name, current_ar_date, previous_ar_date, founding_date, expected_code, expected_msg', [
    ('SUCCESS', '2018-08-05', '2017-08-05', '1900-07-01', None, None),
    ('NO_AR_DATE', None, '2017-08-05', '1900-07-01',
     HTTPStatus.BAD_REQUEST, [{'error': 'Annual Report Date must be a valid date.',
                               'path': 'filing/annualReport/annualReportDate'}]),
    ('NO_FUTURE_FILINGS',
     (datetime.utcnow() + datedelta.YEAR).date().isoformat(),  # current_ar_date a year in the future
     '2017-08-05', '1900-07-01',
     HTTPStatus.BAD_REQUEST, [{'error': 'Annual Report Date cannot be in the future.',
                               'path': 'filing/annualReport/annualReportDate'}]),
    ('AR_BEFORE_LAST_AR', '2016-08-05', '2017-08-05', '1900-07-01',
     HTTPStatus.BAD_REQUEST, [
         {'error': 'Annual Report Date cannot be before a previous Annual Report or the Founding Date.',
          'path': 'filing/annualReport/annualReportDate'}]),
    ('NO_LAST_AR_NOT_AFTER_FOUNDING', '2016-08-05', None, '1900-07-01',
     HTTPStatus.BAD_REQUEST, [
         {'error': 'Annual Report Date must be the next Annual Report in contiguous order.',
          'path': 'filing/annualReport/annualReportDate'}]),
    ('NO_LAST_AR_BEFORE_FOUNDING', '2016-08-05', None, '2017-08-05',
     HTTPStatus.BAD_REQUEST, [
         {'error': 'Annual Report Date cannot be before a previous Annual Report or the Founding Date.',
          'path': 'filing/annualReport/annualReportDate'}]),
    ('LAST_AR_NOT_CONTIGUOUS_ORDER', '2019-08-05', '2017-08-05', '1900-07-01',
     HTTPStatus.BAD_REQUEST, [
         {'error': 'Annual Report Date must be the next Annual Report in contiguous order.',
          'path': 'filing/annualReport/annualReportDate'}]),
])
def test_validate_ar_year(app, test_name, current_ar_date, previous_ar_date, founding_date,
                          expected_code, expected_msg):
    """Assert that ARs filing/annualReport/annualReportDate is valid."""
    # setup
    identifier = 'CP1234567'
    business = Business(identifier=identifier)
    business.founding_date = datetime.fromisoformat(founding_date)

    previous_ar = copy.deepcopy(ANNUAL_REPORT)
    previous_ar['filing']['business']['identifier'] = identifier
    current_ar = copy.deepcopy(previous_ar)

    previous_ar['filing']['annualReport']['annualReportDate'] = previous_ar_date
    current_ar['filing']['annualReport']['annualReportDate'] = current_ar_date

    # Test it
    with app.app_context():
        err = validate_ar_year(business=business,
                               previous_annual_report=previous_ar,
                               current_annual_report=current_ar)
    # Validate the outcome
    if not expected_code and not err:
        assert err is expected_code
    else:
        assert err.code == expected_code
        assert err.msg == expected_msg
