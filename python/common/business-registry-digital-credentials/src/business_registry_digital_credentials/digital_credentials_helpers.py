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

"""This provides helper functions for digital credentials."""

from typing import List, Union
from flask import current_app

from business_model.models import Business, CorpType, DCDefinition, User, DCBusinessUser
from .digital_credentials_rules import DigitalCredentialsRulesService


def log_something():
    """This is a placeholder function to ensure the code is complete."""
    current_app.logger.error("This is a placeholder function for digital credentials helpers1234.")
    # log to standard output
    # print("This is a placeholder function for digital credentials XXXXXXXXXXXXXXXXXXXXXXXXX.")
    pass


def get_digital_credential_data(
    business_user: DCBusinessUser,
    credential_type: DCDefinition.CredentialType,
    self_attested_roles: Union[List[str], None] = None,
) -> List[dict[str, str]]:
    """Get the data for a digital credential."""
    if credential_type == DCDefinition.CredentialType.business:
        rules = DigitalCredentialsRulesService()

        business = business_user.business
        user = business_user.user

        credential_id = f"{business_user.id:08}"
        business_type = get_business_type(business)
        registered_on_dateint = get_registered_on_dateint(business)
        company_status = get_company_status(business)
        family_name = get_family_name(user)
        given_names = get_given_names(user)
        roles = get_roles(user, business, rules, self_attested_roles)

        return [
            {"name": "credential_id", "value": credential_id or ""},
            {"name": "identifier", "value": business.identifier or ""},
            {"name": "business_name", "value": business.legal_name or ""},
            {"name": "business_type", "value": business_type or ""},
            {"name": "cra_business_number", "value": business.tax_id or ""},
            {"name": "registered_on_dateint", "value": registered_on_dateint or ""},
            {"name": "company_status", "value": company_status or ""},
            {"name": "family_name", "value": family_name or ""},
            {"name": "given_names", "value": given_names or ""},
            {"name": "role", "value": ", ".join(roles) or ""},
        ]

    return None


def get_or_create_business_user(user: User, business: Business) -> DCBusinessUser:
    """Get or create business user."""
    business_user = DCBusinessUser.find_by(business_id=business.id, user_id=user.id)
    if not business_user:
        business_user = DCBusinessUser(business_id=business.id, user_id=user.id)
        business_user.save()
    return business_user


def get_business_type(business: Business) -> str:
    """Get business type description."""
    business_type = CorpType.find_by_id(business.legal_type)
    return business_type.full_desc if business_type else business.legal_type


def get_company_status(business: Business) -> str:
    """Get company status."""
    return Business.State(business.state).name


def get_registered_on_dateint(business: Business) -> str:
    """Get registered on date in YYYYMMDD format."""
    return business.founding_date.strftime("%Y%m%d") if business.founding_date else ""


def get_family_name(user: User) -> str:
    """Get family name in uppercase."""
    return (user.lastname or "").strip().upper()


def get_given_names(user: User) -> str:
    """Get given names in uppercase."""
    return " ".join([x.strip() for x in [user.firstname, user.middlename] if x and x.strip()]).upper()


def get_roles(
    user: User, business: Business, rules: DigitalCredentialsRulesService, self_attested_roles: Union[List[str], None]
) -> List[str]:
    """Get roles for the user in the business."""

    def valid_party_role_filter(party_role) -> bool:
        """Filter party roles in both preconditions and self-attested roles."""
        return party_role.role in preconditions and party_role.role in self_attested_roles

    party_roles = []
    preconditions = rules.get_preconditions(user, business)

    has_preconditions = preconditions is not None and len(preconditions)
    only_use_self_attested_roles = has_preconditions and self_attested_roles is not None and len(self_attested_roles)
    may_attach_role = not has_preconditions or only_use_self_attested_roles

    if may_attach_role:
        if rules.user_has_business_party_role(user, business):
            party_roles += rules.user_business_party_roles(user, business)
        if rules.user_has_filing_party_role(user, business):
            party_roles += rules.user_filing_party_roles(user, business)

        if only_use_self_attested_roles:
            # Ensures that the user cant attach roles that are not stated in the preconditions
            party_roles = list(filter(valid_party_role_filter, party_roles))

    return list(map(lambda party_role: party_role.role.replace("_", " ").title(), party_roles))


def extract_invitation_message_id(json_message: dict) -> str:
    """Extract the invitation message id from the json message."""
    if "invitation" in json_message and json_message["invitation"] is not None:
        invitation_message_id = json_message["invitation"]["@id"]
    else:
        invitation_message_id = json_message["invitation_msg_id"]
    return invitation_message_id
