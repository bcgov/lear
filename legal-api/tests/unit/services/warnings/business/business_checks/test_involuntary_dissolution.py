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
from datedelta import datedelta
from registry_schemas.example_data import CHANGE_OF_ADDRESS, FILING_HEADER, RESTORATION

from legal_api.models import Batch, BatchProcessing, Business
from legal_api.services.warnings.business.business_checks import WarningType, BusinessWarningCodes
from legal_api.services.warnings.business.business_checks.involuntary_dissolution import (
    _get_modified_warning_data,
    check_business,
)
from legal_api.utils.datetime import datetime
from tests.unit.models import (
    factory_batch,
    factory_batch_processing,
    factory_business,
    factory_completed_filing,
    factory_pending_filing,
)


RESTORATION_FILING = copy.deepcopy(FILING_HEADER)
RESTORATION_FILING['filing']['restoration'] = RESTORATION

CHANGE_OF_ADDRESS_FILING = copy.deepcopy(FILING_HEADER)
CHANGE_OF_ADDRESS_FILING['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS

FUTURE_TRIGGER_DATE = datetime.utcnow() + datedelta(days=10)
PAST_TRIGGER_DATE = datetime.utcnow() + datedelta(days=-10)


@pytest.mark.parametrize('test_name, no_dissolution, batch_status, batch_processing_status', [
    ('NOT_ELIGIBLE', True, None, None),
    ('ELIGIBLE_AR_OVERDUE', False, 'PROCESSING', 'COMPLETED'),
    ('ELIGIBLE_TRANSITION_OVERDUE', False, 'PROCESSING', 'COMPLETED'),
    ('ELIGIBLE_AR_OVERDUE_FUTURE_EFFECTIVE_FILING_HAS_WARNINGS', False, 'PROCESSING', 'COMPLETED'),
    ('IN_DISSOLUTION_AR_OVERDUE', False, 'PROCESSING', 'PROCESSING'),
    ('IN_DISSOLUTION_TRANSITION_OVERDUE', False, 'PROCESSING', 'PROCESSING'),
    ('IN_DISSOLUTION_AR_OVERDUE_FUTURE_EFFECTIVE_FILING_HAS_WARNINGS', False, 'PROCESSING', 'PROCESSING'),
])
def test_check_business(session, test_name, no_dissolution, batch_status, batch_processing_status):
    """Test the check_business function."""
    identifier = 'BC7654321'
    business = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP.value, no_dissolution=no_dissolution)
    target_date = datetime.utcnow() + datedelta(days=72)
    meta_data = {
        'overdueARs': True,
        'overdueTransition': False,
        'warningsSent': 2,
        'targetDissolutionDate': target_date.date().isoformat()
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
        batch_processing.meta_data = meta_data
        batch_processing.save()

    if 'FUTURE_EFFECTIVE_FILING' in test_name:
        factory_pending_filing(business, CHANGE_OF_ADDRESS_FILING)

    result = check_business(business)

    if test_name == 'NOT_ELIGIBLE':
        assert len(result) == 0
    else:
        if test_name.startswith('IN_DISSOLUTION'):
            assert len(result) == 2
            assert result[1]['code'] == 'DISSOLUTION_IN_PROGRESS'
            assert result[1]['message'] == 'Business is in the process of involuntary dissolution.'
            assert result[1]['warningType'] == WarningType.INVOLUNTARY_DISSOLUTION

            res_meta_data = result[1]['data']
            assert res_meta_data == meta_data

            if 'TRANSITION_OVERDUE' in test_name:
                assert res_meta_data['overdueTransition'] == True
            else:
                assert res_meta_data['overdueARs'] == True
        else:
            assert len(result) == 1

        warning = result[0]
        if 'TRANSITION_OVERDUE' in test_name:
            assert warning['code'] == BusinessWarningCodes.TRANSITION_NOT_FILED_AFTER_12_MONTH_RESTORATION.value
            assert warning['message'] == 'Transition filing not filed. Eligible for involuntary dissolution.'
            assert warning['warningType'] == WarningType.NOT_IN_GOOD_STANDING
        else:
            assert warning['code'] == 'MULTIPLE_ANNUAL_REPORTS_NOT_FILED'
            assert warning['message'] == 'Multiple annual reports not filed. Eligible for involuntary dissolution.'
            assert warning['warningType'] == WarningType.NOT_IN_GOOD_STANDING


@pytest.mark.parametrize('test_name, batch_processing_step, trigger_date, expected_warning_date', [
    (
        'LEVEL1',
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        FUTURE_TRIGGER_DATE,
        FUTURE_TRIGGER_DATE + datedelta(days=30)
    ),
    (
        'LEVEL1_PAST',
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        PAST_TRIGGER_DATE,
        datetime.utcnow() + datedelta(days=30)
    ),
    (
        'LEVEL2',
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
        FUTURE_TRIGGER_DATE,
        FUTURE_TRIGGER_DATE
    ),
    (
        'LEVEL2_PAST',
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
        PAST_TRIGGER_DATE,
        datetime.utcnow()
    )
])
def test_get_modified_warning_data(session, test_name, batch_processing_step, trigger_date, expected_warning_date):
    """Test _get_modified_warning_data function."""
    identifier = 'BC7654321'
    business = factory_business(identifier=identifier, entity_type=Business.LegalTypes.COMP)
    batch = factory_batch()
    batch_processing = factory_batch_processing(
        batch_id=batch.id,
        business_id=business.id,
        identifier=identifier,
        step=batch_processing_step,
        trigger_date=trigger_date
    )
    batch_processing.meta_data = {}
    batch_processing.save()

    data = _get_modified_warning_data(batch_processing)

    assert 'targetDissolutionDate' in data
    assert data['targetDissolutionDate'] == expected_warning_date.date().isoformat()
