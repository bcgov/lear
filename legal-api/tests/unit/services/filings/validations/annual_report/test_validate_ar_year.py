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
from tests.unit.models import factory_business


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
    business = Business(identifier=identifier, last_ledger_timestamp=previous_ar_date)
    business.founding_date = datetime.fromisoformat(founding_date)

    if previous_ar_date:
        business.last_ar_date = datetime.fromisoformat(previous_ar_date)
        business.last_ar_year = datetime.fromisoformat(previous_ar_date).year

    previous_ar = copy.deepcopy(ANNUAL_REPORT)
    current_ar = copy.deepcopy(previous_ar)

    current_ar['filing']['annualReport']['annualReportDate'] = current_ar_date

    # Test it
    with app.app_context():
        err = validate_ar_year(business=business,
                               current_annual_report=current_ar)
    # Validate the outcome
    if not expected_code and not err:
        assert err is expected_code
    else:
        assert err.code == expected_code
        assert err.msg == expected_msg


@pytest.mark.parametrize('test_name, identifier, founding_date, previous_ar_date, legal_type, expected_ar_min_date, expected_ar_max_date', [
    ('BCOMP first AR', 'BC1234567', '2021-06-29', None, Business.LegalTypes.BCOMP.value, '2022-06-29', '2022-08-28'),
    ('BCOMP last AR issued', 'BC1234567', '1900-07-01', '2021-03-03', Business.LegalTypes.BCOMP.value, '2022-03-03', '2022-05-02'),
    ('COOP last AR issued in due time', 'CP1234567', '1900-07-01', '2021-03-03', Business.LegalTypes.COOP.value, '2022-01-01', '2022-04-30'),
    ('COOP last AR issued overdue', 'CP1234567', '1900-07-01', '2021-11-03', Business.LegalTypes.COOP.value, '2022-01-01', '2022-04-30'),    
    ('COOP founded in the end of the year', 'CP1234567', '2021-12-31', None, Business.LegalTypes.COOP.value, '2022-01-01', '2022-04-30'),    
])
def test_ar_dates(app, session, test_name, identifier, founding_date, previous_ar_date, legal_type, expected_ar_min_date, expected_ar_max_date):
    """Assert min and max dates for Annual Report are correct."""
    # setup
    previous_ar_datetime = datetime.fromisoformat(previous_ar_date) if previous_ar_date else None
    business = factory_business(identifier, datetime.fromisoformat(founding_date), previous_ar_datetime, legal_type)
    ar_min_date, ar_max_date = business.get_ar_dates(2022)
    
    assert ar_min_date.isoformat() == expected_ar_min_date
    assert ar_max_date.isoformat() == expected_ar_max_date
