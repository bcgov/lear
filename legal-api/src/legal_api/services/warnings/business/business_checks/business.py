# Copyright © 2022 Province of British Columbia
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

"""Service to check compliancy for a business."""
from legal_api.models import Business
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService

from .corps import check_business as corps_check
from .firms import check_business as firms_check
from .involuntary_dissolution import check_business as involuntary_dissolution_check


def check_business(business: any) -> list:
    """Check business for warnings."""
    result = []

    if business.legal_type in \
            (Business.LegalTypes.SOLE_PROP.value,
             Business.LegalTypes.PARTNERSHIP.value):
        result = firms_check(business)
    elif business.legal_type in Business.CORPS:
        result = corps_check(business)

    if business.legal_type in InvoluntaryDissolutionService.ELIGIBLE_TYPES:
        result.extend(involuntary_dissolution_check(business))

    return result
