# Copyright © 2023 Province of British Columbia
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
"""Test suite to ensure AGM Location Change is validated correctly."""
import copy
from http import HTTPStatus

import pytest

from business_common.utils.datetime import datetime
from business_common.utils.legislation_datetime import LegislationDatetime
from legal_api.services.filings.validations.validation import validate
from registry_schemas.example_data import AGM_LOCATION_CHANGE, FILING_HEADER
from tests.unit.models import factory_business


# Sentinel for cases whose blank/whitespace rule moved into business-schemas: the filing is now
# rejected by schema validation (HTTP 422) instead of the legal-api business check (HTTP 400).
SCHEMA_REJECTED = 'SCHEMA_REJECTED'

# Set far enough in the past that founding date never becomes the binding floor
OLD_FOUNDING_DATE = datetime.utcnow().replace(year=datetime.utcnow().year - 10)


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('INVALID_YEAR', HTTPStatus.UNPROCESSABLE_ENTITY, SCHEMA_REJECTED),
        ('FAIL_YEAR-3', HTTPStatus.BAD_REQUEST, None),
        ('FAIL_YEAR+2', HTTPStatus.BAD_REQUEST, None),
        ('SUCCESS-2', None, None),
        ('SUCCESS+1', None, None),
        ('SUCCESS', None, None)
    ]
)
def test_validate_agm_year(session, mocker, test_name, expected_code, message, monkeypatch):
    """Assert validate agm year for an established business (founding date well outside the lookback window)."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag, default=None: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-agm-location-change-entities' else default
    )
    business = factory_business(identifier='BC1234567', entity_type='BC', founding_date=OLD_FOUNDING_DATE)
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)
    filing['filing']['header']['name'] = 'agmLocationChange'

    current_year = LegislationDatetime.now().year
    expected_min = current_year - 2
    expected_max = current_year + 1

    if test_name == 'INVALID_YEAR':
        filing['filing']['agmLocationChange']['year'] = 'invalid'
    elif test_name == 'FAIL_YEAR-3':
        filing['filing']['agmLocationChange']['year'] = str(current_year - 3)
    elif test_name == 'FAIL_YEAR+2':
        filing['filing']['agmLocationChange']['year'] = str(current_year + 2)
    elif test_name == 'SUCCESS-2':
        filing['filing']['agmLocationChange']['year'] = str(current_year - 2)
    elif test_name == 'SUCCESS+1':
        filing['filing']['agmLocationChange']['year'] = str(current_year + 1)
    elif test_name == 'SUCCESS':
        filing['filing']['agmLocationChange']['year'] = str(current_year)
    err = validate(business, filing)

    # validate outcomes
    if message == SCHEMA_REJECTED:
        assert err is not None
        assert err.code == HTTPStatus.UNPROCESSABLE_ENTITY
    elif not test_name.startswith('SUCCESS'):
        assert expected_code == err.code
        assert f'AGM year must be between {expected_min} and {expected_max}.' == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, founding_years_ago, year_offset_from_now',
    [
        # business founded less than 2 years ago: founding year should raise the floor
        # above the default lookback year
        ('FAIL_BEFORE_FOUNDING_YEAR', 1, -2),
        ('SUCCESS_AT_FOUNDING_YEAR', 1, -1),
        # business founded this year: floor should equal the current year
        ('FAIL_BEFORE_FOUNDING_THIS_YEAR', 0, -1),
        ('SUCCESS_FOUNDING_THIS_YEAR', 0, 0),
    ]
)
def test_validate_agm_year_founding_date_floor(
    session, mocker, test_name, founding_years_ago, year_offset_from_now, monkeypatch
):
    """Assert AGM year cannot be set to a year before the business's founding year."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag, default=None: "BC BEN CC ULC C CBEN CCC CUL" if flag == 'supported-agm-location-change-entities' else default
    )
    current_year = LegislationDatetime.now().year
    founding_date = datetime.utcnow().replace(year=current_year - founding_years_ago)
    business = factory_business(identifier='BC1234567', entity_type='BC', founding_date=founding_date)

    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)
    filing['filing']['header']['name'] = 'agmLocationChange'
    filing['filing']['agmLocationChange']['year'] = str(current_year + year_offset_from_now)

    err = validate(business, filing)

    founding_year = current_year - founding_years_ago
    expected_min = max(current_year - 2, founding_year)
    expected_max = current_year + 1

    if test_name.startswith('FAIL'):
        assert err is not None
        assert err.code == HTTPStatus.BAD_REQUEST
        assert f'AGM year must be between {expected_min} and {expected_max}.' == err.msg[0]['error']
    else:
        assert not err


@pytest.mark.parametrize(
    'test_name, reason, expected_code, message',
    [
        ('EMPTY', '', HTTPStatus.UNPROCESSABLE_ENTITY, SCHEMA_REJECTED),
        ('ONLY_WHITESPACE', '     ', HTTPStatus.UNPROCESSABLE_ENTITY, SCHEMA_REJECTED),
        ('VALID_REASON', 'Test Reason', None, None),
        ('VALID_REASON_WITH_SPACES', '   Valid Reason   ', None, None),
    ]
)
def test_validate_agm_reason(session, mocker, test_name, reason, expected_code, message, monkeypatch):
    """Assert validate agm reason"""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag, default=None: "BC BEN CC ULC C CBEN CCC CUL" if flag == 'supported-agm-location-change-entities' else default
    )
    business = factory_business(identifier='BC1234567', entity_type='BC', founding_date=OLD_FOUNDING_DATE)
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)
    filing['filing']['header']['name'] = 'agmLocationChange'
    filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year)

    filing['filing']['agmLocationChange']['reason'] = reason

    err = validate(business, filing)

    # validate outcomes
    if message == SCHEMA_REJECTED:
        assert err is not None
        assert err.code == HTTPStatus.UNPROCESSABLE_ENTITY
    elif expected_code:
        assert expected_code == err.code
        assert message == err.msg[0]['error']
    else:
        assert not err
