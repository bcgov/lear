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
"""Test Change of Director basic validations."""
import copy
# from datetime import date
from http import HTTPStatus

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings import validate
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit import CHANGE_OF_DIRECTORS_SAMPLE as CHANGE_OF_DIRECTORS


@pytest.mark.parametrize(
    'test_name, now, delivery_region_1, delivery_country_1, delivery_region_2, delivery_country_2,'
    'expected_code, expected_msg',
    [
        ('SUCCESS', datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
         'BC', 'CA', 'BC', 'CA',
         None, None),
        ('SUCCESS-NON_CA_COUNTRY', datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
         'AM', 'DE', 'AM', 'DE',
         None, None),
        ('Director[1] Nonsense Country', datetime(2001, 8, 5, 12, 0, 0, 0, tzinfo=timezone.utc),
         'BC', 'CA', 'BC', 'nonsense',
         HTTPStatus.BAD_REQUEST, [
             {'error': 'Address Country must resolve to a valid ISO-2 country.',
              'path': '/filing/changeOfDirectors/directors/1/deliveryAddress/addressCountry'}]),
    ])
def test_validate_cod_basic(session, test_name, now,
                            delivery_region_1, delivery_country_1, delivery_region_2, delivery_country_2,
                            expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a basic COD can be validated."""
    # setup
    identifier = 'CP1234567'
    founding_date = now - datedelta.YEAR
    business = Business(identifier=identifier,
                        last_ledger_timestamp=founding_date,
                        founding_date=founding_date)

    # convert 'now' to an effective date with 0 time in the legislation timezone, same as the UI does
    effective_date = LegislationDatetime.as_legislation_timezone(now)
    effective_date = effective_date.replace(hour=0, minute=0, second=0, microsecond=0)
    effective_date = LegislationDatetime.as_utc_timezone(effective_date)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = now.date().isoformat()
    f['filing']['header']['effectiveDate'] = effective_date.isoformat()
    f['filing']['header']['name'] = 'changeOfDirectors'
    f['filing']['business']['identifier'] = identifier

    cod = copy.deepcopy(CHANGE_OF_DIRECTORS)
    cod['directors'][0]['deliveryAddress']['addressCountry'] = delivery_country_1
    cod['directors'][0]['deliveryAddress']['addressRegion'] = delivery_region_1
    cod['directors'][1]['deliveryAddress']['addressCountry'] = delivery_country_2
    cod['directors'][1]['deliveryAddress']['addressRegion'] = delivery_region_2
    f['filing']['changeOfDirectors'] = cod

    # perform test
    with freeze_time(now):
        err = validate(business, f)
        if err:
            print(err.msg)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
