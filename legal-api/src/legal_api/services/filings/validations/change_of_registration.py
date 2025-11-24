# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Change of Registration filing."""
from http import HTTPStatus  # pylint: disable=wrong-import-order
from typing import Optional

from flask_babel import _ as babel

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    find_updated_keys_for_firms,
    validate_name_request,
    validate_offices_addresses,
    validate_parties_addresses,
)
from legal_api.services.filings.validations.registration import (
    validate_naics,
    validate_offices,
    validate_party,
    validate_registration_court_order,
)
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService


def validate(business: Business, filing: dict) -> Optional[Error]:
    """Validate the Change of Registration filing."""
    filing_type = "changeOfRegistration"
    if not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid filing is required.")}])

    msg = []
    for item in find_updated_keys_for_firms(business, filing, filing_type):
        if flags.is_on("enabled-deeper-permission-action"):
            if (item.get("is_dba") and
                (
                    item.get("name_changed") or
                    item.get("address_changed") or
                    item.get("delivery_address_changed") or
                    item.get("email_changed")
                )
            ):
                required_permission = ListActionsPermissionsAllowed.FIRM_EDITABLE_DBA.value
                message = "Permission Denied - You do not have permissions edit DBA in this filing."
                error = PermissionService.check_user_permission(required_permission, message=message)
                if error:
                    return error
            elif not item.get("is_dba") and item.get("email_changed"):
                required_permission = ListActionsPermissionsAllowed.FIRM_EDITABLE_EMAIL_ADDRESS.value
                message = "Permission Denied - You do not have permissions edit email in this filing."
                error = PermissionService.check_user_permission(required_permission, message=message)
                if error:
                    return error
    if filing.get("filing", {}).get("changeOfRegistration", {}).get("nameRequest", None):
        msg.extend(validate_name_request(filing, business.legal_type, filing_type))
    if filing.get("filing", {}).get("changeOfRegistration", {}).get("parties", None):
        msg.extend(validate_party(filing, business.legal_type, filing_type))
        msg.extend(validate_parties_addresses(filing, filing_type))
    if filing.get("filing", {}).get("changeOfRegistration", {}).get("offices", None):
        msg.extend(validate_offices(filing, filing_type))
        msg.extend(validate_offices_addresses(filing, filing_type))

    msg.extend(validate_naics(filing, filing_type))
    msg.extend(validate_registration_court_order(filing, filing_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
