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
from freezegun import freeze_time
from legal_api.models import Business
from legal_api.services.filings.validations.annual_report import validate_ar_year
from registry_schemas.example_data import ANNUAL_REPORT

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


@pytest.mark.parametrize(
    'test_name, founding_date, previous_ar_date, legal_type, expected_ar_min_date,' +
    'expected_ar_max_date, previous_ar_year, next_year, today',
    [
        ('BEN first AR', '2011-06-29', None, Business.LegalTypes.BCOMP.value,
         '2012-06-29', '2012-08-28', None, 2012, '2022-07-14'),
        ('BEN last AR filed', '1900-07-01', '2011-07-03', Business.LegalTypes.BCOMP.value,
         '2012-07-01', '2012-08-30', 2011, 2012, '2022-07-14'),
        ('BEN max AR date equals today (2022-07-14)', '1900-07-01', '2021-07-03', Business.LegalTypes.BCOMP.value,
         '2022-07-01', '2022-07-14', 2021, 2022, '2022-07-14'),
        ('BEN 2021', '1900-06-01', '2020-07-03', Business.LegalTypes.BCOMP.value,
         '2021-06-01', '2021-07-14', 2020, 2021, '2021-07-14'),
        ('BEN 2024', '2024-02-29', None, Business.LegalTypes.BCOMP.value,  # Leap year
         '2025-03-01', '2025-04-30', None, 2025, '2025-05-30'),

        ('BC first AR', '2011-06-29', None, Business.LegalTypes.COMP.value,
         '2012-06-29', '2012-08-28', None, 2012, '2022-07-14'),
        ('BC last AR filed', '1900-07-01', '2011-07-03', Business.LegalTypes.COMP.value,
         '2012-07-01', '2012-08-30', 2011, 2012, '2022-07-14'),
        ('BC max AR date equals today (2022-07-14)', '1900-07-01', '2021-07-03', Business.LegalTypes.COMP.value,
         '2022-07-01', '2022-07-14', 2021, 2022, '2022-07-14'),
        ('BC 2021', '1900-06-01', '2020-07-03', Business.LegalTypes.COMP.value,
         '2021-06-01', '2021-07-14', 2020, 2021, '2021-07-14'),

        ('ULC first AR', '2011-06-29', None, Business.LegalTypes.BC_ULC_COMPANY.value,
         '2012-06-29', '2012-08-28', None, 2012, '2022-07-14'),
        ('ULC last AR filed', '1900-07-01', '2011-07-03', Business.LegalTypes.BC_ULC_COMPANY.value,
         '2012-07-01', '2012-08-30', 2011, 2012, '2022-07-14'),
        ('ULC max AR date equals today (2022-07-14)', '1900-07-01', '2021-07-03',
         Business.LegalTypes.BC_ULC_COMPANY.value, '2022-07-01', '2022-07-14', 2021, 2022, '2022-07-14'),
        ('ULC 2021', '1900-06-01', '2020-07-03', Business.LegalTypes.BC_ULC_COMPANY.value,
         '2021-06-01', '2021-07-14', 2020, 2021, '2021-07-14'),

        ('CC first AR', '2011-06-29', None, Business.LegalTypes.BC_CCC.value,
         '2012-06-29', '2012-08-28', None, 2012, '2022-07-14'),
        ('CC last AR filed', '1900-07-01', '2011-07-03', Business.LegalTypes.BC_CCC.value,
         '2012-07-01', '2012-08-30', 2011, 2012, '2022-07-14'),
        ('CC max AR date equals today (2022-07-14)', '1900-07-01', '2021-07-03', Business.LegalTypes.BC_CCC.value,
         '2022-07-01', '2022-07-14', 2021, 2022, '2022-07-14'),
        ('CC 2021', '1900-06-01', '2020-07-03', Business.LegalTypes.BC_CCC.value,
         '2021-06-01', '2021-07-14', 2020, 2021, '2021-07-14'),

        ('COOP first AR', '2011-01-01', None, Business.LegalTypes.COOP.value,
         '2012-01-01', '2013-04-30', None, 2012, '2022-07-14'),
        ('COOP founded in the end of the year', '2011-12-31', None, Business.LegalTypes.COOP.value,
         '2012-01-01', '2013-04-30', None, 2012, '2022-07-14'),
        ('COOP AR for 2021', '1900-07-01', '2020-07-03', Business.LegalTypes.COOP.value,
         '2021-01-01', '2021-07-14', 2020, 2021, '2021-07-14'),
        ('COOP AR for 2020 (covid extension)', '1900-07-01', '2019-07-03', Business.LegalTypes.COOP.value,
         '2020-01-01', '2021-10-31', 2019, 2020, '2022-07-14'),
        ('COOP AR for 2020 (covid extension, max date equals today = 2021-07-14)', '1900-07-01', '2019-07-03',
         Business.LegalTypes.COOP.value, '2020-01-01', '2021-07-14', 2019, 2020, '2021-07-14'),
        ('COOP founded in 2019 (covid extension)', '2019-07-01', None, Business.LegalTypes.COOP.value,
         '2020-01-01', '2021-10-31', None, 2020, '2022-07-14'),
    ])
def test_ar_dates(
        app, session, test_name, founding_date, previous_ar_date, legal_type,
        expected_ar_min_date, expected_ar_max_date, previous_ar_year, next_year, today):
    """Assert min and max dates for Annual Report are correct."""
    now = datetime.fromisoformat(today + 'T12:00:00+00:00')
    with freeze_time(now):
        # setup
        previous_ar_datetime = datetime.fromisoformat(previous_ar_date) if previous_ar_date else None
        business = factory_business('CP1234567',
                                    datetime.fromisoformat(founding_date + 'T12:00:00+00:00'),
                                    previous_ar_datetime,
                                    legal_type)
        ar_min_date, ar_max_date = business.get_ar_dates(next_year)

        assert ar_min_date.isoformat() == expected_ar_min_date
        assert ar_max_date.isoformat() == expected_ar_max_date
