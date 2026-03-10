# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test suite to ensure Corpse business checks work correctly for businesses in liquidation."""
import copy

import pytest
from psycopg2.tz import FixedOffsetTimezone
from datedelta import datedelta

from legal_api.models import Business
from legal_api.services.warnings.business import check_business
from legal_api.services.warnings.business.business_checks import WarningType, BusinessWarningCodes
from legal_api.utils.datetime import datetime, date
from tests.unit.models import factory_business

FOUNDING_DATE = datetime(2023, 3, 3)
IN_LIQUIDATION_DATE = datetime(2024, 6, 10, 0, 0, tzinfo=FixedOffsetTimezone(0))

@pytest.mark.parametrize('test_name, founding_date, in_liquidation_date, last_lr_year, expected_meta_data', [
    ('NOT_IN_LIQUIDATION', datetime.now(), None, None, {}),
    ('IN_LIQUIDATION', FOUNDING_DATE, IN_LIQUIDATION_DATE, None,
     {
         'inLiquidationDate': IN_LIQUIDATION_DATE,
         'lastLiquidationReportYear': None,
         'nextLiquidationReportMinDate': date(2025, 3, 2)}
    ),
    ('IN_LIQUIDATION_lr_year', FOUNDING_DATE, IN_LIQUIDATION_DATE, 2025,
     {
         'inLiquidationDate': IN_LIQUIDATION_DATE,
         'lastLiquidationReportYear': 2025,
         'nextLiquidationReportMinDate': date(2026, 3, 2)}
    ),
    # Should not happen, but need to make sure it still returns for this case
    ('IN_LIQUIDATION_no_in_liquidation_date', FOUNDING_DATE, None, None,
     {
         'inLiquidationDate': None,
         'lastLiquidationReportYear': None,
         'nextLiquidationReportMinDate': None}
    )
])
def test_check_business(session, test_name, founding_date, in_liquidation_date, last_lr_year, expected_meta_data):
    """Test the check_business function."""
    identifier = 'BC7654321'
    business = factory_business(identifier=identifier,
                                entity_type=Business.LegalTypes.COMP.value,
                                founding_date=founding_date,
                                in_liquidation_date=in_liquidation_date,
                                last_lr_year=last_lr_year)

    if test_name != 'NOT_IN_LIQUIDATION':
        business.in_liquidation = True
        business.save()

    result = check_business(business)

    if test_name == 'NOT_IN_LIQUIDATION':
        assert len(result) == 0
    else:
        assert len(result) == 1
        assert result[0]['code'] == BusinessWarningCodes.LIQUIDATION_IN_PROGRESS
        assert result[0]['message'] == 'This business is in the process of Liquidation.'
        assert result[0]['warningType'] == WarningType.LIQUIDATION

        res_meta_data = result[0]['data']
        assert res_meta_data == expected_meta_data
