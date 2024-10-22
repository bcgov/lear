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

"""Service to check warnings for a business."""
from legal_api.models import Business
from legal_api.utils.util import print_execution_time

from .business import check_business


@print_execution_time
def check_warnings(business: Business) -> list:
    """Check warnings for a business."""
    result = []

    # Currently only checks for missing business info warnings but in future other warning checks can be included
    # e.g. compliance checks - result.extend(check_compliance(business))
    result.extend(check_business(business))

    return result
