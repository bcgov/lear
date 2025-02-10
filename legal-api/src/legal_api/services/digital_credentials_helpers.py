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

from legal_api.models import Business, CorpType, DCDefinition, DCIssuedBusinessUserCredential, Party, PartyRole, User
from legal_api.services.digital_credentials_rules import DigitalCredentialsRulesService
from legal_api.services.digital_credentils_utils import user_party_role


def get_digital_credential_data(user: User, business: Business, credential_type: DCDefinition.CredentialType):
    """Get the data for a digital credential."""
    if credential_type == DCDefinition.CredentialType.business:
        rules = DigitalCredentialsRulesService()

        # Find the credential id from dc_issued_business_user_credentials and if there isn't one create one
        if not (issued_business_user_credential := DCIssuedBusinessUserCredential.find_by(
                business_id=business.id, user_id=user.id)):
            issued_business_user_credential = DCIssuedBusinessUserCredential(
                business_id=business.id, user_id=user.id)
            issued_business_user_credential.save()

        credential_id = f'{issued_business_user_credential.id:08}'

        if (business_type := CorpType.find_by_id(business.legal_type)):
            business_type = business_type.full_desc
        else:
            business_type = business.legal_type

        registered_on_dateint = ''
        if business.founding_date:
            registered_on_dateint = business.founding_date.strftime(
                '%Y%m%d')

        company_status = Business.State(business.state).name

        family_name = (user.lastname or '').strip().upper()

        given_names = ' '.join(
            [x.strip() for x in [user.firstname, user.middlename] if x and x.strip()]).upper()

        roles = []
        business_party_role_mapping = {
            Business.LegalTypes.SOLE_PROP.value: PartyRole.RoleTypes.PROPRIETOR.value,
            Business.LegalTypes.PARTNERSHIP.value: PartyRole.RoleTypes.PARTNER.value,
            Business.LegalTypes.BCOMP.value: PartyRole.RoleTypes.DIRECTOR.value
        }
        if business.legal_type in business_party_role_mapping:
            party_role_type = business_party_role_mapping[business.legal_type]
            if rules.has_party_role(user, business, party_role_type):
                party_role = user_party_role(
                    user, business, party_role_type)
                roles.append(
                    (party_role.role or '').replace('_', ' ').title())

            if business.legal_type == Business.LegalTypes.BCOMP.value and rules.is_completing_party(user, business):
                roles.append('Incorporator'.title())

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


def extract_invitation_message_id(json_message: dict):
    """Extract the invitation message id from the json message."""
    if 'invitation' in json_message and json_message['invitation'] is not None:
        invitation_message_id = json_message['invitation']['@id']
    else:
        invitation_message_id = json_message['invitation_msg_id']
    return invitation_message_id
