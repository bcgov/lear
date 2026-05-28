# Copyright © 2025 Province of British Columbia
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

"""This provides auth functions for digital credentials.

Both functions here require Flask request context (``g`` + ``request_ctx``).
The queue service never reaches this path — DBC access enforcement is a
legal-api / HTTP concern.
"""

from flask import g
from flask.globals import request_ctx
from flask_jwt_oidc import JwtManager

from business_model.models.business import Business
from business_model.models.user import User

from .digital_credentials_rules import DigitalCredentialsRulesService

STAFF_ROLE = "staff"


def are_digital_credentials_allowed(
    business: Business, jwt: JwtManager, allowed_business_types: list[str]
) -> bool:
    """Return True if the business is allowed to have/view digital credentials.

    ``allowed_business_types`` is the feature-flag-resolved list (required — pass ``[]``
    to deny). The caller (legal-api) loads the LaunchDarkly flag and forwards the value.
    """
    is_staff = jwt.contains_role(request_ctx.current_user, [STAFF_ROLE])
    if is_staff:
        # Staff do not have digital credentials
        return False

    if not (user := User.find_by_jwt_token(g.jwt_oidc_token_info)):
        return False

    rules = DigitalCredentialsRulesService()
    return rules.are_digital_credentials_allowed(user, business, allowed_business_types)


def get_digital_credentials_preconditions(business: Business) -> dict[str, list[str]]:
    """Return the preconditions for digital credentials."""
    if not (user := User.find_by_jwt_token(g.jwt_oidc_token_info)):
        return {}

    rules = DigitalCredentialsRulesService()
    return {
        "attestBusiness": business.legal_name if business else None,
        "attestName": user.display_name if user else None,
        "attestRoles": rules.get_preconditions(user, business) if user and business else [],
    }
