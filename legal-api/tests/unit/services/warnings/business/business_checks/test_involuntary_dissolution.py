# Copyright © 2024 Province of British Columbia
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
"""Test suite to ensure Corpse business checks work correctly."""
import copy
import pytest
import json
from legal_api.models import Batch, Business
from tests.unit.models import (
    factory_batch,
    factory_batch_processing,
    factory_business,
    factory_completed_filing
)
from legal_api.services.warnings.business.business_checks import WarningType
from legal_api.services.warnings.business.business_checks.involuntary_dissolution import check_business
from legal_api.utils.datetime import datetime

from datedelta import datedelta
from registry_schemas.example_data import FILING_HEADER, RESTORATION, TRANSITION_FILING_TEMPLATE

RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION

@pytest.mark.parametrize('test_name, no_dissolution, batch_status, batch_processing_status', [
    ('NOT_ELIGIBLE', True, None, None),
    ('ELIGIBLE_AR_OVERDUE', False, 'PROCESSING', 'COMPLETED'),
    ('ELIGIBLE_TRANSITION_OVERDUE', False, 'PROCESSING', 'COMPLETED'),
    ('IN_DISSOLUTION_AR_OVERDUE', False, 'PROCESSING', 'PROCESSING'),
    ('IN_DISSOLUTION_TRANSITION_OVERDUE', False, 'PROCESSING', 'PROCESSING')
])
def test_check_business(session, test_name, no_dissolution, batch_status, batch_processing_status):
    """Test the check_business function."""
    identifier = 'BC7654321'
    business = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value, no_dissolution=no_dissolution)
    meta_data = {
        'overdueARs': True,
        'overdueTransition': False,
        'warningsSent': 2,
        'dissolutionTargetDate': '2025-02-01'
    }
    if 'TRANSITION_OVERDUE' in test_name:
        effective_date = datetime.utcnow() - datedelta(years=3)
        factory_completed_filing(business, RESTORATION_FILING, filing_type='restoration', filing_date=effective_date)
        meta_data['overdueTransition'] = True

    if not no_dissolution:
        batch = factory_batch(
            batch_type = Batch.BatchType.INVOLUNTARY_DISSOLUTION,
            status = batch_status,
        )
        batch_processing = factory_batch_processing(
            batch_id = batch.id,
            business_id = business.id,
            identifier = business.identifier,
            status = batch_processing_status,
        )
        batch_processing.meta_data = json.dumps(meta_data)
        batch_processing.save()

    result = check_business(business)

    if test_name == 'NOT_ELIGIBLE':
        assert len(result) == 0
    else:
        if test_name.startswith('IN_DISSOLUTION'):
            assert len(result) == 2
            assert result[1]['code'] == 'DISSOLUTION_IN_PROGRESS'
            assert result[1]['message'] == 'Business is in the process of involuntary dissolution.'
            assert result[1]['warningType'] == WarningType.INVOLUNTARY_DISSOLUTION
            res_meta_data = json.loads(result[1]['data'])
            assert res_meta_data == meta_data
            if 'TRANSITION_OVERDUE' in test_name:
                assert res_meta_data['overdueTransition'] == True
            else:
                assert res_meta_data['overdueARs'] == True
        else:
            assert len(result) == 1
        
        warning = result[0]
        if 'TRANSITION_OVERDUE' in test_name:
            assert warning['code'] == 'TRANSITION_NOT_FILED'
            assert warning['message'] == 'Transition filing not filed. Eligible for involuntary dissolution.'
            assert warning['warningType'] == WarningType.NOT_IN_GOOD_STANDING
        else:
            assert warning['code'] == 'MULTIPLE_ANNUAL_REPORTS_NOT_FILED'
            assert warning['message'] == 'Multiple annual reports not filed. Eligible for involuntary dissolution.'
            assert warning['warningType'] == WarningType.NOT_IN_GOOD_STANDING
