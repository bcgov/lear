# Copyright © 2024 Province of British Columbia
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

"""Service to check involuntary dissolution for a business."""
from datedelta import datedelta
from flask import current_app

from legal_api.models import BatchProcessing, Business
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService
from legal_api.utils.datetime import datetime

from . import BusinessWarningCodes, WarningType


def check_business(business: Business) -> list:
    """Check involuntary dissolution for warnings."""
    result = []

    ar_overdue_warning = {
        'code': BusinessWarningCodes.MULTIPLE_ANNUAL_REPORTS_NOT_FILED,
        'message': 'Multiple annual reports not filed. Eligible for involuntary dissolution.',
        'warningType': WarningType.NOT_IN_GOOD_STANDING
    }
    transition_warning = {
        'code': BusinessWarningCodes.TRANSITION_NOT_FILED_AFTER_12_MONTH_RESTORATION.value,
        'message': 'Transition filing not filed. Eligible for involuntary dissolution.',
        'warningType': WarningType.NOT_IN_GOOD_STANDING
    }

    eligibility, details = InvoluntaryDissolutionService.check_business_eligibility(
        business.identifier, InvoluntaryDissolutionService.EligibilityFilters(exclude_future_effective_filing=True))
    if eligibility:
        if details.transition_overdue:
            result.append(transition_warning)
        elif details.ar_overdue:
            result.append(ar_overdue_warning)
    elif batch_datas := InvoluntaryDissolutionService.get_in_dissolution_batch_processing(business.id):
        batch_processing, _ = batch_datas
        _, dis_details = InvoluntaryDissolutionService.check_business_eligibility(
            business.identifier, InvoluntaryDissolutionService.EligibilityFilters(
                exclude_in_dissolution=False, exclude_future_effective_filing=True
            )
        )

        # dis_details is None when the account is not included in FF filter
        if not dis_details:
            return result

        if dis_details.transition_overdue:
            result.append(transition_warning)
        elif dis_details.ar_overdue:
            result.append(ar_overdue_warning)

        data = _get_modified_warning_data(batch_processing)

        result.append({
            'code': BusinessWarningCodes.DISSOLUTION_IN_PROGRESS,
            'data': data,
            'message': 'Business is in the process of involuntary dissolution.',
            'warningType': WarningType.INVOLUNTARY_DISSOLUTION
        })

    return result


def _get_modified_warning_data(batch_processing: BatchProcessing) -> dict:
    """Return involuntary disssolution warning data based on rules."""
    meta_data = batch_processing.meta_data if batch_processing.meta_data else {}

    trigger_date = batch_processing.trigger_date
    current_date = datetime.utcnow()
    modified_target_date = None
    if batch_processing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1:
        modified_target_date = max(current_date, trigger_date) + datedelta(days=current_app.config.get('STAGE_2_DELAY'))
    elif batch_processing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2:
        modified_target_date = max(current_date, trigger_date)

    if modified_target_date:
        meta_data = {
            **meta_data,
            'targetDissolutionDate': modified_target_date.date().isoformat()
        }

    return meta_data
