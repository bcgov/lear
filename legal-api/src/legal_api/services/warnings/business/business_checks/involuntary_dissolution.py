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
from legal_api.models import Business
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService

from . import BusinessWarningCodes, WarningType


def check_business(business: Business) -> list:
    """Check involuntary dissolution for warnings."""
    result = []

    ar_overdue_warning = {
        'code': BusinessWarningCodes.MULTIPLE_ANNUAL_REPORTS_NOT_FILED,
        'message': 'Multiple annual reports not filed.  Eligible for involuntary dissolution.',
        'warningType': WarningType.NOT_IN_GOOD_STANDING
    }
    transition_warning = {
        'code': BusinessWarningCodes.TRANSITION_NOT_FILED,
        'message': 'Transition filing not filed.  Eligible for involuntary dissolution.',
        'warningType': WarningType.NOT_IN_GOOD_STANDING
    }

    eligibility, details = InvoluntaryDissolutionService.check_business_eligibility(business.identifier, True)
    if eligibility:
        if details.transition_overdue:
            result.append(transition_warning)
        elif details.ar_overdue:
            result.append(ar_overdue_warning)
    elif batch_datas := InvoluntaryDissolutionService.get_in_dissolution_batch_processing(business.id):
        batch_processing, _ = batch_datas
        _, dis_details = InvoluntaryDissolutionService.check_business_eligibility(business.identifier, False, True)
        if dis_details.transition_overdue:
            result.append(transition_warning)
        elif dis_details.ar_overdue:
            result.append(ar_overdue_warning)
        result.append({
            'code': BusinessWarningCodes.DISSOLUTION_IN_PROGRESS,
            'data': batch_processing.meta_data,
            'message': 'Business is in the process of involuntary dissolution.',
            'warningType': WarningType.INVOLUNTARY_DISSOLUTION
        })

    return result
