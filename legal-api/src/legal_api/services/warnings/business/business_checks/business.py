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

"""Service to check compliancy for a LegalEntity."""
from .firms import check_business as firms_check  # noqa: I003
from legal_api.services.warnings.business.business_checks import WarningType

def check_business(business: any) -> list:
    """Check business for warnings."""
    result = []

    if business.is_firm:
        result = firms_check(business)

    ting_info = Business.check_if_ting(business.identifier)
    if ting_info:
        result =[  
                    {
                        "code": "AMALGAMATING_BUSINESS", 
                        "message": "This business is part of a future effective amalgamation.", 
                        "warningType": WarningType.FUTURE_EFFECTIVE_AMALGAMATION,
                        "data": {
                            "amalgamationDate": ting_info 
                        }
                    }
                ]
    return result
