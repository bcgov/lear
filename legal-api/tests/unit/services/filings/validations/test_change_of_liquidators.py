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
from datetime import date, timedelta
from http import HTTPStatus
import pytest

from business_common.utils.legislation_datetime import LegislationDatetime
from legal_api.services.filings import validate
from tests.unit.services.filings.validations import lists_are_equal
from tests.unit.models import factory_business
from registry_schemas.example_data import CHANGE_OF_LIQUIDATORS, FILING_HEADER


@pytest.mark.parametrize(
    'test_name, roles, expected_code, expected_msg',
    [
        (
            'Valid liquidator with valid meta',
            [{'roleType': 'Liquidator', 'meta': {'appointmentMethod': 'court', 'courtOrderNumber': '12345'}}],
            None,
            None
        ),
        (
            'Invalid liquidator with missing meta key (schema 422)',
            [{'roleType': 'Liquidator'}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "'meta' is a required property",
                    'path': 'changeOfLiquidators/relationships/0/roles/0'
                }
            ]
        ),
        (
            'Invalid liquidator with meta None (schema 422)',
            [{'roleType': 'Liquidator', 'meta': None}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "None is not of type 'object'",
                    'path': 'changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
        (
            'Invalid liquidator meta non-dict (schema 422)',
            [{'roleType': 'Liquidator', 'meta': 'not_a_dict'}],
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'context': [],
                    'error': "'not_a_dict' is not of type 'object'",
                    'path': 'changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
        (
            'Invalid liquidator meta property (business rule 400)',
            [{
                'roleType': 'Liquidator', 
                'meta': {
                    'appointmentMethod': 'court', 
                    'courtOrderNumber': '12345', 
                    'unauthorizedKey': 'invalid'
                }
            }],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid meta property: unauthorizedKey.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/meta/unauthorizedKey'
                }
            ]
        ),
        (
            'Invalid role without meta',
            [{'roleType': 'Director'}],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid role type for this filing.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/roleType'
                }
            ]
        ),
        (
            'Invalid role with meta',
            [{'roleType': 'Director', 'meta': {'appointmentMethod': 'company'}}],
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': 'Invalid role type for this filing.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/roleType'
                },
                {
                    'error': 'Cannot submit meta properties for this role.',
                    'path': '/filing/changeOfLiquidators/relationships/0/roles/0/meta'
                }
            ]
        ),
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


@pytest.mark.parametrize(
    'test_name, filing_sub_type, in_liquidation, day_offset, raw_date, expected_code, expected_msg',
    [
        (
            'Valid appointLiquidator date (not in liquidation)',
            'appointLiquidator',
            False,
            -5,
            None,
            None,
            None
        ),
        (
            'Valid appointLiquidator current date (not in liquidation)',
            'appointLiquidator',
            False,
            0,
            None,
            None,
            None
        ),
        (
            'Missing date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            None,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' is required when business is not yet in liquidation.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Future date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            1,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Invalid format date for appointLiquidator (not in liquidation)',
            'appointLiquidator',
            False,
            None,
            '2026/05/15',
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'error': "'2026/05/15' is not a 'date'",
                    'path': 'changeOfLiquidators/changeOfLiquidatorsDate',
                    'context': []
                }
            ]
        ),
        (
            'Optional date omitted for appointLiquidator when already in liquidation',
            'appointLiquidator',
            True,
            None,
            None,
            None,
            None
        ),
        (
            'Optional date provided in the past when already in liquidation',
            'appointLiquidator',
            True,
            -10,
            None,
            None,
            None
        ),
        (
            'Optional date in the future when already in liquidation',
            'appointLiquidator',
            True,
            2,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Valid intentToLiquidate past date',
            'intentToLiquidate',
            False,
            -3,
            None,
            None,
            None
        ),
        (
            'Valid intentToLiquidate current date',
            'intentToLiquidate',
            False,
            0,
            None,
            None,
            None
        ),
        (
            'Future date for intentToLiquidate',
            'intentToLiquidate',
            False,
            1,
            None,
            HTTPStatus.BAD_REQUEST,
            [
                {
                    'error': "'changeOfLiquidatorsDate' cannot be in the future.",
                    'path': '/filing/changeOfLiquidators/changeOfLiquidatorsDate'
                }
            ]
        ),
        (
            'Invalid calendar day format for intentToLiquidate',
            'intentToLiquidate',
            False,
            None,
            '2026-02-31',
            HTTPStatus.UNPROCESSABLE_ENTITY,
            [
                {
                    'error': "'2026-02-31' is not a 'date'",
                    'path': 'changeOfLiquidators/changeOfLiquidatorsDate',
                    'context': []
                }
            ]
        ),
    ]
)
def test_validate_col_dates(
    session, test_name, filing_sub_type, in_liquidation, day_offset, raw_date, expected_code, expected_msg
):
    """Assert changeOfLiquidatorsDate validations."""
    identifier = 'BC1234567'
    business = factory_business(identifier)
    business.in_liquidation = in_liquidation

    today_legislation = LegislationDatetime.datenow()

    f = copy.deepcopy(FILING_HEADER)
    f['filing']['header']['date'] = today_legislation.isoformat()
    f['filing']['header']['name'] = 'changeOfLiquidators'
    f['filing']['business']['identifier'] = identifier

    col = copy.deepcopy(CHANGE_OF_LIQUIDATORS)
    col['type'] = filing_sub_type

    if in_liquidation:
        col.pop('offices')

    if raw_date is not None:
        col['changeOfLiquidatorsDate'] = raw_date
    elif day_offset is not None:
        col['changeOfLiquidatorsDate'] = (today_legislation + timedelta(days=day_offset)).isoformat()
    else:
        col.pop('changeOfLiquidatorsDate', None)

    f['filing']['changeOfLiquidators'] = col

    err = validate(business, f)

    if expected_code:
        assert err is not None
        assert err.code == expected_code
        assert lists_are_equal(err.msg, expected_msg)
    else:
        assert err is None