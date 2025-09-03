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
from registry_schemas.example_data import AGM_LOCATION_CHANGE, FILING_HEADER

from legal_api.services.filings.validations.validation import validate
from legal_api.utils.datetime import datetime
from legal_api.utils.legislation_datetime import LegislationDatetime

from tests.unit.models import factory_business


@pytest.mark.parametrize(
    'test_name, expected_code, message',
    [
        ('INVALID_YEAR', HTTPStatus.BAD_REQUEST, 'Invalid AGM year.'),
        ('FAIL_YEAR-3', HTTPStatus.BAD_REQUEST, 'AGM year must be between -2 or +1 year from current year.'),
        ('FAIL_YEAR+2', HTTPStatus.BAD_REQUEST, 'AGM year must be between -2 or +1 year from current year.'),
        ('SUCCESS-2', None, None),
        ('SUCCESS+1', None, None),
        ('SUCCESS', None, None)
    ]
)
def test_validate_agm_year(session, mocker, test_name, expected_code, message, monkeypatch):
    """Assert validate agm year."""
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'supported-agm-location-change-entities' else {}
    )
    business = factory_business(identifier='BC1234567', entity_type='BC', founding_date=datetime.utcnow())
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['agmLocationChange'] = copy.deepcopy(AGM_LOCATION_CHANGE)
    filing['filing']['header']['name'] = 'agmLocationChange'

    if test_name == 'INVALID_YEAR':
        filing['filing']['agmLocationChange']['year'] = 'invalid'
    elif test_name == 'FAIL_YEAR-3':
        filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year - 3)
    elif test_name == 'FAIL_YEAR+2':
        filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year + 2)
    elif test_name == 'SUCCESS-2':
        filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year - 2)
    elif test_name == 'SUCCESS+1':
        filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year + 1)
    elif test_name == 'SUCCESS':
        filing['filing']['agmLocationChange']['year'] = str(LegislationDatetime.now().year)
    err = validate(business, filing)

    # validate outcomes
    if not test_name.startswith('SUCCESS'):
        assert expected_code == err.code
        if message:
            assert message == err.msg[0]['error']
    else:
        assert not err
