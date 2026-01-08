# Copyright © 2025 Province of British Columbia
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

# pylint: disable=too-many-lines
"""This manages all of the permissions service."""
from enum import Enum
from http import HTTPStatus
from typing import Optional

from flask import current_app, g

from legal_api.core.filing import Filing as CoreFiling
from legal_api.errors import Error
from legal_api.models.authorized_role_permission import AuthorizedRolePermission
from legal_api.services import authz, flags
from legal_api.services.cache import cache
from legal_api.services.request_context import get_request_context


class ListFilingsPermissionsAllowed(str, Enum):
    """Define an enum for filing permissions checks."""

    ADDRESS_CHANGE_FILING = "ADDRESS_CHANGE_FILING"
    AGM_CHG_LOCATION_FILING = "AGM_CHG_LOCATION_FILING"
    AGM_EXTENSION_FILING = "AGM_EXTENSION_FILING"
    ALTERATION_FILING = "ALTERATION_FILING"
    AMALGAMATION_FILING = "AMALGAMATION_FILING"
    ANNUAL_REPORT_FILING = "ANNUAL_REPORT_FILING"
    CONSENT_AMALGAMATION_OUT_FILING = "CONSENT_AMALGAMATION_OUT_FILING"
    CONSENT_CONTINUATION_OUT_FILING = "CONSENT_CONTINUATION_OUT_FILING"
    CONTINUATION_IN_FILING = "CONTINUATION_IN_FILING"
    CORRECTION_FILING = "CORRECTION_FILING"
    COURT_ORDER_FILING = "COURT_ORDER_FILING"
    DISSOLUTION_ADMIN_FILING = "ADMIN_DISSOLUTION_FILING"
    DISSOLUTION_DELAY_FILING = "DELAY_DISSOLUTION_FILING"
    DISSOLUTION_FIRM_FILING = "FIRM_DISSOLUTION_FILING"
    DISSOLUTION_INVOLUNTARY_FILING = "DISSOLUTION_INVOLUNTARY_FILING"
    DISSOLUTION_VOLUNTARY_FILING = "VOLUNTARY_DISSOLUTION_FILING"
    DIRECTOR_CHANGE_FILING = "DIRECTOR_CHANGE_FILING"
    FIRM_CHANGE_FILING = "FIRM_CHANGE_FILING"
    FIRM_CONVERSION_FILING = "FIRM_CONVERSION_FILING"
    INCORPORATION_APPLICATION_FILING = "INCORPORATION_APPLICATION_FILING"
    NOTICE_WITHDRAWAL_FILING = "NOTICE_WITHDRAWAL_FILING"
    OFFICER_CHANGE_FILING = "OFFICER_CHANGE_FILING"
    REGISTRATION_FILING = "REGISTRATION_FILING"
    RESTORATION_REINSTATEMENT_FILING = "RESTORATION_REINSTATEMENT_FILING"
    SPECIAL_RESOLUTION_FILING = "SPECIAL_RESOLUTION_FILING"
    STAFF_FILINGS = "STAFF_FILINGS"
    TRANSITION_FILING = "TRANSITION_FILING"
    
class ListActionsPermissionsAllowed(str, Enum):
    """Define an enum for action permissions checks."""

    ADD_ENTITY_NO_AUTHENTICATION = "ADD_ENTITY_NO_AUTHENTICATION"
    AML_OVERRIDES = "AML_OVERRIDES"
    COURT_ORDER_POA = "COURT_ORDER_POA"
    DETAIL_COMMENTS = "DETAIL_COMMENTS"
    EDITABLE_CERTIFY_NAME = "EDITABLE_CERTIFY_NAME"
    EDITABLE_COMPLETING_PARTY = "EDITABLE_COMPLETING_PARTY"
    FIRM_ADD_BUSINESS = "FIRM_ADD_BUSINESS"
    FIRM_EDITABLE_DBA = "FIRM_EDITABLE_DBA"
    FIRM_EDITABLE_EMAIL_ADDRESS = "FIRM_EDITABLE_EMAIL_ADDRESS"
    FIRM_NO_MIN_START_DATE = "FIRM_NO_MIN_START_DATE"
    FIRM_REPLACE_PERSON = "FIRM_REPLACE_PERSON"
    OVERRIDE_NIGS="OVERRIDE_NIGS"
    STAFF_COMMENTS = "STAFF_COMMENTS"
    STAFF_PAYMENT="STAFF_PAYMENT"

class PermissionService:
    """Service to manage permissions for user roles."""

    @staticmethod
    def get_authorized_permissions_for_user():
        """Return a JSON response containing the authorized permissions for the current user."""
        authorized_role = PermissionService.get_authorized_user_role()
        if not authorized_role:
            return []

        cache_key = f"authorized_permissions_{authorized_role}"
        cached_permissions = cache.get(cache_key)

        if cached_permissions:
            authorized_permissions = cached_permissions
        else:
            authorized_permissions = AuthorizedRolePermission.get_authorized_permissions_by_role_name(authorized_role)
            cache.set(cache_key, authorized_permissions)

        return authorized_permissions

    @staticmethod
    def get_authorized_user_role(token_info: Optional[dict] = None) -> str:
        """Return the first matching authorized role from the JWT, based on priority."""
        role_priority = [
            authz.STAFF_ROLE,
            authz.SBC_STAFF_ROLE,
            authz.CONTACT_CENTRE_STAFF_ROLE,
            authz.MAXIMUS_STAFF_ROLE,
            authz.PUBLIC_USER,
        ]

        if token_info is None:
            token_info = getattr(g, "jwt_oidc_token_info", {}) or {}

        roles_in_token = token_info.get("realm_access", {}).get("roles", [])
        for role in role_priority:
            if role in roles_in_token:
                return role
        return None

    @staticmethod
    def get_filing_permission_mapping(legal_type: str, filing_sub_type: str) -> dict:
        """Return dictionary containing rules for filings are allowed for different roles."""
        def get_dissolution_mapping():
            from legal_api.services.filings.validations.dissolution import DissolutionTypes
            permission_granted = ""
            dissolution_mapping = {
                DissolutionTypes.VOLUNTARY: ListFilingsPermissionsAllowed.DISSOLUTION_VOLUNTARY_FILING.value,
                DissolutionTypes.INVOLUNTARY: ListFilingsPermissionsAllowed.DISSOLUTION_INVOLUNTARY_FILING.value,
                DissolutionTypes.ADMINISTRATIVE: ListFilingsPermissionsAllowed.DISSOLUTION_ADMIN_FILING.value,
            }
            permission_granted = dissolution_mapping.get(filing_sub_type)
            if legal_type in ["FM", "SP", "GP", "LLP"]:
                permission_granted = ListFilingsPermissionsAllowed.DISSOLUTION_FIRM_FILING.value
            return permission_granted

        return {
            CoreFiling.FilingTypes.AGMEXTENSION.value:
                ListFilingsPermissionsAllowed.AGM_EXTENSION_FILING.value,
            CoreFiling.FilingTypes.AGMLOCATIONCHANGE.value:
                ListFilingsPermissionsAllowed.AGM_CHG_LOCATION_FILING.value,
            CoreFiling.FilingTypes.ALTERATION.value:
                ListFilingsPermissionsAllowed.ALTERATION_FILING.value,
            CoreFiling.FilingTypes.AMALGAMATIONAPPLICATION.value:
                ListFilingsPermissionsAllowed.AMALGAMATION_FILING.value,
            CoreFiling.FilingTypes.ANNUALREPORT.value:
                ListFilingsPermissionsAllowed.ANNUAL_REPORT_FILING.value,
            CoreFiling.FilingTypes.CHANGEOFADDRESS.value:
                ListFilingsPermissionsAllowed.ADDRESS_CHANGE_FILING.value,
            CoreFiling.FilingTypes.CHANGEOFREGISTRATION.value:
                ListFilingsPermissionsAllowed.FIRM_CHANGE_FILING.value,
            CoreFiling.FilingTypes.CHANGEOFDIRECTORS.value:
                ListFilingsPermissionsAllowed.DIRECTOR_CHANGE_FILING.value,
            CoreFiling.FilingTypes.CHANGEOFOFFICERS.value:
                ListFilingsPermissionsAllowed.OFFICER_CHANGE_FILING.value,    
            CoreFiling.FilingTypes.CONSENTAMALGAMATIONOUT.value:
                ListFilingsPermissionsAllowed.CONSENT_AMALGAMATION_OUT_FILING.value,
            CoreFiling.FilingTypes.CONSENTCONTINUATIONOUT.value:
                ListFilingsPermissionsAllowed.CONSENT_CONTINUATION_OUT_FILING.value,
            CoreFiling.FilingTypes.CONTINUATIONIN.value:
                ListFilingsPermissionsAllowed.CONTINUATION_IN_FILING.value,
            CoreFiling.FilingTypes.CONVERSION.value:
                ListFilingsPermissionsAllowed.FIRM_CONVERSION_FILING.value,
            CoreFiling.FilingTypes.CORRECTION.value:
                ListFilingsPermissionsAllowed.CORRECTION_FILING.value,
            CoreFiling.FilingTypes.COURTORDER.value:
                ListFilingsPermissionsAllowed.COURT_ORDER_FILING.value,
            CoreFiling.FilingTypes.DISSOLUTION.value:
                get_dissolution_mapping(),
            CoreFiling.FilingTypes.INCORPORATIONAPPLICATION.value:
                ListFilingsPermissionsAllowed.INCORPORATION_APPLICATION_FILING.value,
            CoreFiling.FilingTypes.NOTICEOFWITHDRAWAL.value:
                ListFilingsPermissionsAllowed.NOTICE_WITHDRAWAL_FILING.value,
            CoreFiling.FilingTypes.RESTORATION.value:
                ListFilingsPermissionsAllowed.RESTORATION_REINSTATEMENT_FILING.value,
            CoreFiling.FilingTypes.REGISTRATION.value:
                ListFilingsPermissionsAllowed.REGISTRATION_FILING.value,
            CoreFiling.FilingTypes.SPECIALRESOLUTION.value:
                ListFilingsPermissionsAllowed.SPECIAL_RESOLUTION_FILING.value,
            CoreFiling.FilingTypes.TRANSITION.value:
                ListFilingsPermissionsAllowed.TRANSITION_FILING.value
        }

    @staticmethod
    def find_roles_for_filing_type(filing_type_value: str, legal_type: str, filing_sub_type) -> str:
        """Find roles that are allowed to perform the given filing type."""
        allowable_permissions = PermissionService.get_filing_permission_mapping(legal_type, filing_sub_type)
        roles_with_filing = allowable_permissions.get(filing_type_value, "")
        return roles_with_filing

    @staticmethod
    def has_permissions_for_action(filing_type: str, legal_type: str, filing_sub_type: str) -> bool:
        """Check if the user has permissions for the action per permissions table."""
        authorized_permissions = PermissionService.get_authorized_permissions_for_user()
        if not authorized_permissions or not isinstance(authorized_permissions, list):
            current_app.logger.error("No authorized permissions found for user.")
            return False
        roles_in_filings = PermissionService.find_roles_for_filing_type(filing_type, legal_type, filing_sub_type)
        if roles_in_filings in authorized_permissions:
            return True
        else:
            current_app.logger.warning(f"User does not have permission for filing type: {filing_type}")
        return False

    @staticmethod
    def check_user_permission(required_permission, message: Optional[str] = None) -> Error:
        """Check if the user has the required permission."""
        authorized_permissions = PermissionService.get_authorized_permissions_for_user()
        if required_permission not in authorized_permissions:
            return Error(
                HTTPStatus.FORBIDDEN,
                [{
                    "message": message or f"Permission Denied - You do not have permissions to perform {required_permission} in filing."
                }]
            )
        return None
    
    @staticmethod
    def check_filing_enabled(filing_type: str, filing_sub_type: str) -> Error:
        """Check if a filing type is enabled via FF."""
        filings_to_check = [
            "changeOfLiquidators.appointLiquidator",
            "changeOfLiquidators.ceaseLiquidator",
            "changeOfLiquidators.changeAddressLiquidator",
            "changeOfLiquidators.intentToLiquidate",
            "changeOfLiquidators.liquidationReport",
            "changeOfReceivers.amendReceiver",
            "changeOfReceivers.appointReceiver",
            "changeOfReceivers.ceaseReceiver",
            "changeOfReceivers.changeAddressReceiver",
            "dissolution.delay"
        ]
        filing_key = f"{filing_type}.{filing_sub_type}" if filing_sub_type else filing_type

        if filing_key in filings_to_check:
            request_context = get_request_context()
            enabled_filings_str: str = flags.value("enabled-specific-filings",
                                                   request_context.user,
                                                   request_context.account_id)

            if not filing_key in enabled_filings_str.split(','):
                return Error(
                    HTTPStatus.FORBIDDEN,
                    [{
                        "message": f"Permission Denied - {filing_key} filing is currently not available for this user and/or account."
                    }]
                )
        return None
    
