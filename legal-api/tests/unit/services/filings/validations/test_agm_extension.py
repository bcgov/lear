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
"""Test suite to ensure AGM Extension is validated correctly."""
import copy
from dateutil.relativedelta import relativedelta
from http import HTTPStatus
from unittest.mock import patch

import pytest
from registry_schemas.example_data import FILING_HEADER

from legal_api.services.filings.validations.validation import validate
from legal_api.utils.legislation_datetime import LegislationDatetime
from legal_api.utils.datetime import datetime

from tests.unit.models import factory_business


@pytest.mark.parametrize(
    'test_name, founding_date, agm_ext_json, expected_code, message',
    [
        ('SUCCESS_FIRST_AGM_FIRST_EXT', '2023-10-01', 
         {'year': '2023','isFirstAgm': True, 'extReqForAgmYear': False, 'totalApprovedExt': 6, 'extensionDuration': 6},
         None, None),
        ('FAIL_FIRST_AGM_FIRST_EXT_TOO_LATE', '2020-10-01', {'year': '2023','isFirstAgm': True, 'extReqForAgmYear': False},
         HTTPStatus.BAD_REQUEST, 'Allotted period to request extension has expired.'),
        ('SUCCESS_FIRST_AGM_MORE_EXT', '2022-10-01', 
         {'year': '2023','isFirstAgm': True, 'extReqForAgmYear': True, 'expireDateCurrExt': '2024-10-01', 'totalApprovedExt': 12, 'extensionDuration': 6},
           None, None),
        ('FAIL_FIRST_AGM_MORE_EXT_TOO_LATE', '2022-10-01', {'year': '2023','isFirstAgm': True, 'extReqForAgmYear': True, 'expireDateCurrExt': '2023-12-01'},
         HTTPStatus.BAD_REQUEST, 'Allotted period to request extension has expired.'),
        ('FAIL_FIRST_AGM_MORE_EXT_EXCEED_LIMIT', '2021-10-01', {'year': '2023','isFirstAgm': True, 'extReqForAgmYear': True, 'expireDateCurrExt': '2024-10-01'},
         HTTPStatus.BAD_REQUEST, 'Company has received the maximum 12 months of allowable extensions.'),
        ('SUCCESS_SUBSEQUENT_AGM_FIRST_EXT', '2020-10-01', 
         {'year': '2023','isFirstAgm': False, 'extReqForAgmYear': False, 'prevAgmRefDate':'2023-10-01', 'totalApprovedExt': 6, 'extensionDuration': 6},
           None, None),
        ('FAIL_SUBSEQUENT_AGM_FIRST_EXT_TOO_LATE', '2020-10-01', {'year': '2023','isFirstAgm': False, 'extReqForAgmYear': False, 'prevAgmRefDate':'2022-06-01'},
         HTTPStatus.BAD_REQUEST, 'Allotted period to request extension has expired.'),
        ('SUCCESS_SUBSEQUENT_AGM_MORE_EXT', '2022-10-01',
         {'year': '2023','isFirstAgm': False, 'extReqForAgmYear': True, 'prevAgmRefDate':'2023-06-01', 'expireDateCurrExt':'2024-05-01', 'totalApprovedExt': 12, 'extensionDuration': 1},
         None, None),
        ('FAIL_SUBSEQUENT_AGM_MORE_EXT_TOO_LATE', '2022-10-01',
         {'year': '2023','isFirstAgm': False, 'extReqForAgmYear': True, 'prevAgmRefDate':'2023-06-01', 'expireDateCurrExt':'2023-12-01'},
          HTTPStatus.BAD_REQUEST, 'Allotted period to request extension has expired.'),
        ('FAIL_SUBSEQUENT_AGM_MORE_EXT_EXCEED_LIMIT', '2022-10-01',
         {'year': '2023','isFirstAgm': False, 'extReqForAgmYear': True, 'prevAgmRefDate':'2023-06-01', 'expireDateCurrExt':'2024-06-01'},
          HTTPStatus.BAD_REQUEST, 'Company has received the maximum 12 months of allowable extensions.')
    ]
)
def test_validate_agm_extension(session, mocker, test_name, founding_date, agm_ext_json, expected_code, message, monkeypatch):
    """Assert validate AGM extension."""
    business = factory_business(
        identifier='BC1234567', entity_type='BC', founding_date=LegislationDatetime.as_legislation_timezone_from_date_str(founding_date)
    )
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['agmExtension'] = agm_ext_json
    filing['filing']['header']['name'] = 'agmExtension'
    monkeypatch.setattr(
        'legal_api.services.flags.value',
        lambda flag: "BC BEN CC ULC C CBEN CCC CUL"  if flag == 'support-agm-extension-entities' else {}
    )
    with patch.object(LegislationDatetime, 'now', return_value=LegislationDatetime.as_legislation_timezone_from_date_str('2024-01-01')):
        err = validate(business, filing)
        
        if not test_name.startswith('SUCCESS'):
            assert expected_code == err.code
            if message:
                assert message == err.msg[0]['error']
        else:
            assert not err
