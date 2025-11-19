# Copyright © 2025 Province of British Columbia
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
"""Test suite to ensure Intent to Liquidate is validated correctly."""
import copy
from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from registry_schemas.example_data import FILING_HEADER, INTENT_TO_LIQUIDATE, COURT_ORDER

from legal_api.models import Business
from legal_api.services.filings.validations.intent_to_liquidate import validate
from tests.unit.models import factory_business


@pytest.mark.parametrize(
    'test_status, legal_type, business_state, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'C', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'BEN', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'CBEN', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'ULC', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'CUL', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'CC', Business.State.ACTIVE, None, None),
        ('SUCCESS', 'CCC', Business.State.ACTIVE, None, None)
    ]
)
def test_business_state_validation(session, test_status, legal_type, business_state, expected_code, expected_msg):
    """Assert that business state validation works correctly."""
    # Setup
    business = factory_business('BC1234567', entity_type=legal_type, state=business_state, founding_date=datetime.utcnow())

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['business']['legalType'] = legal_type
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)

    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    # Test
    err = validate(business, filing)

    # Validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, founding_date_offset, liquidation_date_offset, expected_code, expected_msg',
    [
        ('SUCCESS', -365, -30, None, None),  # Founding 1 year ago, liquidation 30 days ago
        ('SUCCESS', -365, 0, None, None),    # Founding 1 year ago, liquidation today
        ('FAIL_DATE_BEFORE_FOUNDING', -365, -400, HTTPStatus.BAD_REQUEST,
         'Date of commencement of liquidation must be later than the business founding date.'),
        ('FAIL_DATE_SAME_AS_FOUNDING', -365, -365, HTTPStatus.BAD_REQUEST,
         'Date of commencement of liquidation must be later than the business founding date.'),
    ]
)
def test_liquidation_date_validation(session, test_status, founding_date_offset, liquidation_date_offset, expected_code, expected_msg):
    """Assert that liquidation date validation works correctly."""
    # Setup founding date
    founding_date = datetime.utcnow() + timedelta(days=founding_date_offset)

    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=founding_date
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)

    liquidation_date = datetime.utcnow() + timedelta(days=liquidation_date_offset)
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = liquidation_date.strftime('%Y-%m-%d')

    # Test
    err = validate(business, filing)

    # Validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, parties, expected_code, expected_msg',
    [
        ('SUCCESS',
         [{'partyName': 'liquidator1', 'roles': [{'roleType': 'Liquidator'}]}],
         None,
         None
        ),
        ('FAIL_NO_LIQUIDATOR',
        [{'partyName': 'party1', 'roles': []}],
        HTTPStatus.BAD_REQUEST,
        'At least one liquidator is required.'
        ),
        ('FAIL_INVALID_ROLE',
         [
             {'partyName': 'liquidator1', 'roles': [{'roleType': 'Liquidator'}]},
             {'partyName': 'party2', 'roles': [{'roleType': 'Custodian'}]}
         ],
         HTTPStatus.BAD_REQUEST,
         'Invalid party role(s) provided: Custodian.'
        ),
    ]
)
def test_parties_validation(session, test_status, parties, expected_code, expected_msg):
    """Assert that parties validation works correctly."""
    # Setup
    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)

    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    filing['filing']['intentToLiquidate']['parties'] = parties

    # Test
    err = validate(business, filing)

    # Validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, office_region, office_country, expected_code, expected_msg',
    [
        ('SUCCESS', 'BC', 'CA', None, None),
        ('FAIL_WRONG_REGION', 'AB', 'CA', HTTPStatus.BAD_REQUEST, "Address Region must be 'BC'."),
        ('FAIL_WRONG_COUNTRY', 'BC', 'US', HTTPStatus.BAD_REQUEST, "Address Country must be 'CA'."),
    ]
)
def test_office_validation(session, test_status, office_region, office_country, expected_code, expected_msg):
    """Assert that office validation works correctly."""
    # Setup
    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)
    
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    if office_region:
        filing['filing']['intentToLiquidate']['offices']['liquidationOffice']['mailingAddress']['addressRegion'] = office_region
        filing['filing']['intentToLiquidate']['offices']['liquidationOffice']['deliveryAddress']['addressRegion'] = office_region
    if office_country:
        filing['filing']['intentToLiquidate']['offices']['liquidationOffice']['mailingAddress']['addressCountry'] = office_country
        filing['filing']['intentToLiquidate']['offices']['liquidationOffice']['deliveryAddress']['addressCountry'] = office_country

    # Test
    err = validate(business, filing)

    # Validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_status, has_court_order, file_number, expected_code, expected_msg',
    [
        ('SUCCESS_NO_COURT_ORDER', False, None, None, None),
        ('SUCCESS_WITH_COURT_ORDER', True, '12345678901234567890', None, None),
        ('FAIL_INVALID_COURT_ORDER', True, None, HTTPStatus.BAD_REQUEST, 'Court order file number is required.'),
    ]
)
def test_court_order_validation(session, test_status, has_court_order, file_number, expected_code, expected_msg):
    """Assert that court order validation works correctly."""
    # Setup
    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)
    
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    if has_court_order:
        court_order = copy.deepcopy(COURT_ORDER)
        if file_number:
            court_order['fileNumber'] = file_number
        else:
            del court_order['fileNumber']
        filing['filing']['intentToLiquidate']['courtOrder'] = court_order
    else:
        # Remove court order if it exists in the template
        if 'courtOrder' in filing['filing']['intentToLiquidate']:
            del filing['filing']['intentToLiquidate']['courtOrder']

    # Test
    err = validate(business, filing)

    # Validate outcomes
    if expected_code or expected_msg:
        assert expected_code == err.code
        assert expected_msg == err.msg[0]['error']
    else:
        assert not err


def test_complete_valid_filing(session):
    """Assert that a complete valid filing passes validation."""
    # Setup
    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)
    
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    # Test
    err = validate(business, filing)

    # Should pass without errors
    assert not err


def test_multiple_liquidators(session):
    """Assert that multiple liquidators are allowed."""
    # Setup
    business = factory_business(
        identifier='BC1234567',
        entity_type='BC',
        state=Business.State.ACTIVE,
        founding_date=datetime.utcnow()
    )

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['name'] = 'intentToLiquidate'
    filing['filing']['intentToLiquidate'] = copy.deepcopy(INTENT_TO_LIQUIDATE)
    
    # Override liquidation date to be after founding date
    future_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    filing['filing']['intentToLiquidate']['dateOfCommencementOfLiquidation'] = future_date

    # Add a second liquidator
    second_liquidator = copy.deepcopy(filing['filing']['intentToLiquidate']['parties'][0])
    second_liquidator['officer']['organizationName'] = 'Second Liquidator Firm Ltd.'
    filing['filing']['intentToLiquidate']['parties'].append(second_liquidator)

    # Test
    err = validate(business, filing)

    # Should pass without errors
    assert not err
