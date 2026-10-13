# Copyright © 2026 Province of British Columbia
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
"""Test Change of Liquidator validation."""
import copy
from datetime import date, datetime, time
from http import HTTPStatus

import datedelta
import pytest

from business_model.models import Business
from legal_api.services.filings import validate
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit.models import factory_business
from registry_schemas.example_data import CHANGE_OF_LIQUIDATORS, FILING_HEADER


@pytest.mark.parametrize(
    'test_name, roles, expected_code, expected_msg',
    [
        (
            'Valid liquidator',
            [{'roleType': 'Liquidator' }],
            None,
            None
        ),
        (
            'Invalid role',
            [{'roleType': 'Director' }],  # Invalid role
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid role type for this filing.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/roleType'
                }
            ]
        )
    ]
)
def test_validate_col_relationships(
    session, test_name, roles, expected_code, expected_msg
):
    """Assert relationship validations for Change of Liquidators."""
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['relationships'][0]['roles'] = roles
    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None


@pytest.mark.parametrize(
    'test_name, mailing_country_region, delivery_country_region, expected_code, expected_msg',
    [
        (
            'Valid office - all BC',
            ['CA', 'BC'],
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Valid office - mailing EX-BC',
            ['CA', 'AB'], # mailing can be outside of BC
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Valid office - mailing EX-CA',
            ['US', 'CA'], # mailing can be outside of Canada
            ['CA', 'BC'],
            None,
            None
        ),
        (
            'Invalid office - delivery EX-CA',
            ['CA', 'BC'],
            ['US', 'BC'], # delivery fails outside of Canada
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Address Country must be 'CA'.",
                    'path': '/filing/changeOfLiquidators/offices/liquidationRecordsOffice'
                }
            ]
        ),
        (
            'Invalid office - delivery EX-BC',
            ['CA', 'BC'],
            ['CA', 'AB'], # delivery fails outside of BC
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "Address Region must be 'BC'.",
                    'path': '/filing/changeOfLiquidators/offices/liquidationRecordsOffice'
                }
            ]
        ),
    ]
)
def test_validate_col_offices(
    session, test_name, mailing_country_region, delivery_country_region, expected_code, expected_msg,
):
    """Assert office validations for Change of Liquidators."""
    identifier = 'BC1234567'
    business = factory_business(identifier)

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = date.today().isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)

    mailing_country = mailing_country_region[0]
    mailing_region = mailing_country_region[1]
    
    delivery_country = delivery_country_region[0]
    delivery_region = delivery_country_region[1]

    office = col['offices']['liquidationRecordsOffice']
    mailing = office['mailingAddress']
    delivery = office['deliveryAddress']

    mailing['addressCountry'] = mailing_country
    mailing['addressRegion'] = mailing_region
    delivery['addressCountry'] = delivery_country
    delivery['addressRegion'] = delivery_region
    
    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None