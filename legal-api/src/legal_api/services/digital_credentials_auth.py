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

"""Legal-api wrapper around the shared DBC auth functions.

Loads the ``dbc-enabled-business-types`` LaunchDarkly flag and forwards the
resolved value into the shared ``business_registry_digital_credentials`` API.
This is the only place in legal-api that knows the LD flag key for DBC.
"""

from business_registry_digital_credentials import (
    are_digital_credentials_allowed as _shared_are_digital_credentials_allowed,
)
from business_registry_digital_credentials import (
    get_digital_credentials_preconditions as _shared_get_digital_credentials_preconditions,
)
from flask import current_app

from business_model.models.business import Business
from flask_jwt_oidc import JwtManager

DBC_ENABLED_BUSINESS_TYPES_FLAG = "dbc-enabled-business-types"


def _get_flags():
    """Return the legal-api flags singleton.

    Wrapped in a function (rather than a top-level import) for two reasons:
    1. Avoids a circular import via ``legal_api.services`` package init.
    2. Gives tests a single, stable patch target — ``_get_flags`` — so they can
       return a stub instead of standing up a LaunchDarkly client.
    """
    from legal_api.services import flags
    return flags


def _resolve_allowed_business_types() -> list[str]:
    """Read the ``dbc-enabled-business-types`` LD flag and return the resolved list.

    Returns ``[]`` if the flag is off or the flag value is malformed. Flag lookup
    passes the request's user/account so LD targeting rules can apply.
    """
    from legal_api.services.request_context import get_request_context

    flags = _get_flags()
    request_context = get_request_context()

    if not flags.is_on(DBC_ENABLED_BUSINESS_TYPES_FLAG,
                       request_context.user, request_context.account_id):
        current_app.logger.warning("%s is OFF", DBC_ENABLED_BUSINESS_TYPES_FLAG)
        return []

    flag_obj = flags.value(DBC_ENABLED_BUSINESS_TYPES_FLAG,
                           request_context.user, request_context.account_id)

    if not isinstance(flag_obj, dict) or "types" not in flag_obj or not isinstance(flag_obj["types"], list):
        current_app.logger.error("Invalid %s flag value: %s", DBC_ENABLED_BUSINESS_TYPES_FLAG, flag_obj)
        return []

    return flag_obj["types"]


def are_digital_credentials_allowed(business: Business, jwt: JwtManager) -> bool:
    """Return True if the business is allowed to have/view digital credentials."""
    return _shared_are_digital_credentials_allowed(
        business, jwt, allowed_business_types=_resolve_allowed_business_types()
    )


def get_digital_credentials_preconditions(business: Business) -> dict[str, list[str]]:
    """Return the preconditions for digital credentials."""
    return _shared_get_digital_credentials_preconditions(business)
