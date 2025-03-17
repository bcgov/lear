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

from legal_api.models import Business, CorpType, DCBusinessUser, DCDefinition, User
from legal_api.services.digital_credentials_rules import DigitalCredentialsRulesService
from legal_api.services.digital_credentials_utils import business_party_role_mapping, user_party_role


def get_digital_credential_data(business_user: DCBusinessUser,
                                credential_type: DCDefinition.CredentialType,
                                preconditions_met: Union[bool, None] = None) -> List[str]:
    """Get the data for a digital credential."""
    if credential_type == DCDefinition.CredentialType.business:
        rules = DigitalCredentialsRulesService()

        business = business_user.business
        user = business_user.user

        credential_id = f'{business_user.id:08}'
        business_type = get_business_type(business)
        registered_on_dateint = get_registered_on_dateint(business)
        company_status = get_company_status(business)
        family_name = get_family_name(user)
        given_names = get_given_names(user)
        roles = get_roles(user, business, rules, preconditions_met)

        return [
            {
                'name': 'credential_id',
                'value':  credential_id or ''
            },
            {
                'name': 'identifier',
                'value': business.identifier or ''
            },
            {
                'name': 'business_name',
                'value': business.legal_name or ''
            },
            {
                'name': 'business_type',
                'value': business_type or ''
            },
            {
                'name': 'cra_business_number',
                'value': business.tax_id or ''
            },
            {
                'name': 'registered_on_dateint',
                'value': registered_on_dateint or ''
            },
            {
                'name': 'company_status',
                'value': company_status or ''
            },
            {
                'name': 'family_name',
                'value': family_name or ''
            },
            {
                'name': 'given_names',
                'value': given_names or ''
            },
            {
                'name': 'role',
                'value': ', '.join(roles) or ''
            }
        ]

    return None


def get_or_create_business_user(user: User, business: Business) -> DCBusinessUser:
    """
    Get or create business user.

    DEPRECATED: This function is deprecated and will be removed in future releases.
    """
    business_user = DCBusinessUser.find_by(
        business_id=business.id, user_id=user.id)
    if not business_user:
        business_user = DCBusinessUser(
            business_id=business.id, user_id=user.id)
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
    return business.founding_date.strftime('%Y%m%d') if business.founding_date else ''


def get_family_name(user: User) -> str:
    """Get family name in uppercase."""
    return (user.lastname or '').strip().upper()


def get_given_names(user: User) -> str:
    """Get given names in uppercase."""
    return ' '.join([x.strip() for x in [user.firstname, user.middlename] if x and x.strip()]).upper()


def get_roles(user: User,
              business: Business,
              rules: DigitalCredentialsRulesService,
              preconditions_met: Union[bool, None]) -> List[str]:
    """Get roles for the user in the business."""
    roles = []
    preconditions = rules.get_preconditions(user, business)
    can_attach_role = (preconditions is None) or (len(preconditions) == 0) or (
        len(preconditions) and preconditions_met is True)

    if business.legal_type in business_party_role_mapping:
        party_role_type = business_party_role_mapping[business.legal_type]
        if rules.has_party_role(user, business, party_role_type) and can_attach_role:
            party_role = user_party_role(user, business, party_role_type)
            roles.append((party_role.role or '').replace('_', ' ').title())

    if business.legal_type == Business.LegalTypes.BCOMP.value:
        if rules.is_completing_party(user, business) and can_attach_role:
            roles.append('incorporator'.title())

    return roles


def extract_invitation_message_id(json_message: dict) -> str:
    """Extract the invitation message id from the json message."""
    if 'invitation' in json_message and json_message['invitation'] is not None:
        invitation_message_id = json_message['invitation']['@id']
    else:
        invitation_message_id = json_message['invitation_msg_id']
    return invitation_message_id
