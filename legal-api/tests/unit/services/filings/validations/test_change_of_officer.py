# Copyright © 2025 Province of British Columbia
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
"""Test Change of Officer validation."""
import copy
from datetime import date
from http import HTTPStatus

import datedelta
import pytest
from freezegun import freeze_time
from registry_schemas.example_data import CHANGE_OF_OFFICERS, FILING_HEADER

from legal_api.models import Business
from legal_api.services.filings import validate
from legal_api.utils.datetime import datetime, timezone
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests.unit.services.filings.validations import lists_are_equal


@pytest.mark.parametrize(
    'test_name, address_type, country, expected_code, expected_msg',
    [
        (
            'Valid CA mailing address',
            'mailingAddress',
            'CA',
            None,
            None
        ),
        (
            'Valid non-CA mailing address',
            'mailingAddress',
            'US',
            None,
            None
        ),
        (
            'Valid CA delivery address',
            'deliveryAddress',
            'CA',
            None,
            None
        ),
        (
            'Valid non-CA delivery address',
            'deliveryAddress',
            'US',
            None,
            None
        ),
        (
            'Invalid mailing address',
            'mailingAddress',
            'invalid',
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Address Country must resolve to a valid ISO-2 country.',
                    'path': '/filing/changeOfOfficers/relationships/0/mailingAddress/addressCountry'
                }
            ]
        ),
        (
            'Invalid delivery address',
            'deliveryAddress',
            'invalid',
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Address Country must resolve to a valid ISO-2 country.',
                    'path': '/filing/changeOfOfficers/relationships/0/deliveryAddress/addressCountry'
                }
            ]
        )
    ])
def test_validate_coo(session, test_name, address_type, country, expected_code, expected_msg):  # pylint: disable=too-many-arguments
    """Assert that a COO can be validated."""
    # setup
    now = date.today()
    identifier = 'BC1234567'
    founding_date = now - datedelta.YEAR
    business = Business(
        identifier=identifier,
        last_ledger_timestamp=founding_date,
        founding_date=founding_date
    )

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = now.isoformat()
    f['filing']['header']['name'] = 'changeOfOfficers'
    f['filing']['business']['identifier'] = identifier

    coo = copy.deepcopy(CHANGE_OF_OFFICERS)
    relationship = coo['relationships'][0]
    relationship[address_type]['addressCountry'] = country

    # schema data uses full 'canada' string as country, so need to set the not tested address as a valid value
    if address_type == 'mailingAddress':
        relationship['deliveryAddress']['addressCountry'] = 'CA'
    else:
        relationship['mailingAddress']['addressCountry'] = 'CA'

    f['filing']['changeOfOfficers'] = {
        'relationships': [relationship]
    }

    # perform test
    err = validate(business, f)
    if err:
        print(test_name, err.msg)

    # validate outcomes
    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None
