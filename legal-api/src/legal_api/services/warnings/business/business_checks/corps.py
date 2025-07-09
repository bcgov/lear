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

"""Business checks for corps."""

from legal_api.models import Business
from legal_api.services.warnings.business.business_checks import WarningType, BusinessWarningCodes


def check_business(business: Business) -> list:
    """Check business data."""
    result = []

    result.extend(check_amalgamating_business(business))
    result.extend(check_transition_application(business))

    return result


def check_transition_application(business: Business) -> list:
    """Check if a business is currently pending a post restoration transition application."""
    result = []

    is_transition_needed_but_not_filed = business.transition_needed_but_not_filed()
    if is_transition_needed_but_not_filed:
        result.append({
            'code': BusinessWarningCodes.TRANSITION_NOT_FILED.value,
            'message': 'This Business requires a post restoration transition application to be filed.',
            'warningType': WarningType.NOT_IN_GOOD_STANDING
        })

    return result


def check_amalgamating_business(business: Business) -> list:
    """Check if business is currently pending amalgamation."""
    result = []

    filing = Business.is_pending_amalgamating_business(business.identifier)

    # Check if a matching filing was found and if its effective date is greater than payment completion date
    if filing and filing.effective_date > filing.payment_completion_date:
        result.append({
            'code': 'AMALGAMATING_BUSINESS',
            'message': 'This business is part of a future effective amalgamation.',
            'warningType': WarningType.FUTURE_EFFECTIVE_AMALGAMATION,
            'data': {
                'amalgamationDate': filing.effective_date
            }
        })

    return result
