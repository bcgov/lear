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

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT, CHANGE_OF_ADDRESS, CHANGE_OF_DIRECTORS, FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings import validate


# from tests.unit.models import factory_business, factory_business_mailing_address, factory_filing
@pytest.mark.parametrize(
    'test_name, now, ar_date, agm_date, expected_code, expected_msg',
    [('SUCCESS', date(2020, 9, 17), date(2020, 8, 5), date(2020, 7, 1), None, None),
     ])
def test_validate_ar_basic(session, test_name, now, ar_date, agm_date,
                           expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a basic AR can be validated."""
    # setup
    identifier = 'CP1234567'
    founding_date = ar_date - datedelta.YEAR
    business = Business(identifier=identifier, last_ledger_timestamp=founding_date)
    business.founding_date = founding_date

    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['business']['identifier'] = identifier
    ar['filing']['annualReport']['annualReportDate'] = ar_date.isoformat()
    ar['filing']['annualReport']['annualGeneralMeetingDate'] = agm_date.isoformat()

    # perform test
    with freeze_time(now):
        err = validate(business, ar)

    # validate outcomes
    assert not err


@pytest.mark.parametrize(
    'test_name, now, delivery_region, delivery_country, mailing_region, mailing_country, expected_code, expected_msg',
    [
        ('SUCCESS', date(2020, 9, 17), 'BC', 'CA', 'BC', 'CA', None, None),
        ('FAIL_NOT_BC_DELIVERY_REGION', date(2020, 9, 17), 'AB', 'CA', 'BC', 'CA',
         HTTPStatus.BAD_REQUEST, [{'error': "Address Region must be 'BC'.",
                                   'path':
                                   '/filing/changeOfAddress/offices/registeredOffice/deliveryAddress/addressRegion'}]),
        ('FAIL_NOT_BC_DELIVERY_REGION', date(2020, 9, 17), 'BC', 'CA', 'AB', 'CA',
         HTTPStatus.BAD_REQUEST, [{'error': "Address Region must be 'BC'.",
                                   'path':
                                   '/filing/changeOfAddress/offices/registeredOffice/mailingAddress/addressRegion'}]),
        ('FAIL_ALL_ADDRESS_REGIONS', date(2020, 9, 17), 'WA', 'CA', 'WA', 'CA',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Region must be 'BC'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/mailingAddress/addressRegion'}
        ]),
        ('FAIL_ALL_ADDRESS', date(2020, 9, 17), 'WA', 'US', 'WA', 'US',
         HTTPStatus.BAD_REQUEST, [
             {'error': "Address Region must be 'BC'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/mailingAddress/addressRegion'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/mailingAddress/addressCountry'},
             {'error': "Address Region must be 'BC'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/deliveryAddress/addressRegion'},
             {'error': "Address Country must be 'CA'.",
              'path': '/filing/changeOfAddress/offices/registeredOffice/deliveryAddress/addressCountry'}
        ]),
    ])
def test_validate_coa_basic(session, test_name, now, delivery_region, delivery_country, mailing_region, mailing_country,
                            expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a basic COA can be validated."""
    # setup
    identifier = 'CP1234567'
    founding_date = now - datedelta.YEAR
    business = Business(identifier=identifier, last_ledger_timestamp=founding_date)
    business.founding_date = founding_date

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = now.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier
    f['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS
    office = f['filing']['changeOfAddress']['offices']['registeredOffice']
    office['deliveryAddress']['addressRegion'] = delivery_region
    office['deliveryAddress']['addressCountry'] = delivery_country
    office['mailingAddress']['addressRegion'] = mailing_region
    office['mailingAddress']['addressCountry'] = mailing_country
    # perform test
    with freeze_time(now):
        err = validate(business, f)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, now, delivery_country_1, delivery_country_2, expected_code, expected_msg',
    [
        ('SUCCESS', date(2020, 9, 17), 'CA', 'CA', None, None),
        ('Director[1] Nonsense Country', date(2020, 9, 17), 'CA', 'nonsense',
         HTTPStatus.BAD_REQUEST, [
             {'error': 'Address Country must resolve to a valid ISO-2 country.',
              'path': '/filing/changeOfDirectors/directors/1/deliveryAddress/addressCountry'}]),
    ])
def test_validate_cod_basic(session, test_name, now, delivery_country_1, delivery_country_2,
                            expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a basic COD can be validated."""
    # setup
    identifier = 'CP1234567'
    founding_date = now - datedelta.YEAR
    business = Business(identifier=identifier, last_ledger_timestamp=founding_date)
    business.founding_date = founding_date

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = now.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier

    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    cod['directors'][0]['deliveryAddress']['addressCountry'] = delivery_country_1
    cod['directors'][1]['deliveryAddress']['addressCountry'] = delivery_country_2
    f['filing']['changeOfDirectors'] = cod

    # perform test
    with freeze_time(now):
        err = validate(business, f)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


def lists_are_equal(list_1, list_2) -> bool:
    """Assert that the unordered lists contain the same elements."""
    if len(list_1) != len(list_2):
        return False
    found = False
    for i in list_1:
        for j in list_2:
            if i == j:
                found = True
                break
            else:
                found = False
    return found
