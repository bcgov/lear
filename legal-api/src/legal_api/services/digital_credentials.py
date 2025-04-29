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

"""This provides the service for aca-py api calls."""


import json
from contextlib import suppress
from typing import Optional

import requests

from legal_api.decorators import requires_traction_auth
from legal_api.models import Business, CorpType, DCDefinition, DCIssuedBusinessUserCredential, DCRevocationReason, User


class DigitalCredentialsService:
    """Provides services to do digital credentials using aca-py agent."""

    def __init__(self):
        """Initialize this object."""
        self.app = None

        self.api_url = None
        self.api_token = None
        self.public_schema_did = None
        self.public_issuer_did = None

        self.business_schema_name = None
        self.business_schema_version = None
        self.business_schema_id = None
        self.business_cred_def_id = None

    def init_app(self, app):
        """Initialize digital credentials using aca-py agent."""
        self.app = app

        self.api_url = app.config.get('TRACTION_API_URL')
        self.public_schema_did = app.config.get('TRACTION_PUBLIC_SCHEMA_DID')
        self.public_issuer_did = app.config.get('TRACTION_PUBLIC_ISSUER_DID')

        self.business_schema_name = app.config.get('BUSINESS_SCHEMA_NAME')
        self.business_schema_version = app.config.get('BUSINESS_SCHEMA_VERSION')
        self.business_schema_id = app.config.get('BUSINESS_SCHEMA_ID')
        self.business_cred_def_id = app.config.get('BUSINESS_CRED_DEF_ID')

        with suppress(Exception):
            self._register_business_definition()

    def _register_business_definition(self):
        """Fetch schema and credential definition and save a Business definition."""
        try:
            if not self.business_schema_id:
                self.app.logger.error('Environment variable: BUSINESS_SCHEMA_ID must be configured')
                raise ValueError('Environment variable: BUSINESS_SCHEMA_ID must be configured')

            if not self.business_cred_def_id:
                self.app.logger.error('Environment variable: BUSINESS_CRED_DEF_ID must be configured')
                raise ValueError('Environment variable: BUSINESS_CRED_DEF_ID must be configured')

            ###
            # The following just a sanity check to make sure the schema and
            # credential definition are stored in Traction tenant.
            # These calls also include a ledger lookup to see if the schema
            # and credential definition are published.
            ###

            # Look for a schema first, and copy it into the Traction tenant if it's not there
            if not (schema_id := self._fetch_schema(self.business_schema_id)):
                raise ValueError(f'Schema with id:{self.business_schema_id}' +
                                 ' must be available in Traction tenant storage')

            # Look for a published credential definition first, and copy it into the Traction tenant if it's not there
            if not (credential_definition_id := self._fetch_credential_definition(self.business_cred_def_id)):
                raise ValueError(f'Credential Definition with id:{self.business_cred_def_id}' +
                                 ' must be available in Traction tenant storage')

            # Check for the current Business definition.
            definition = DCDefinition.find_by(
                credential_type=DCDefinition.CredentialType.business,
                schema_id=self.business_schema_id,
                credential_definition_id=self.business_cred_def_id
            )
            if definition and not definition.is_deleted:
                return None

            # Create a new definition and add the new schema_id
            definition = DCDefinition(
                credential_type=DCDefinition.CredentialType.business,
                schema_name=self.business_schema_name,
                schema_version=self.business_schema_version,
                schema_id=schema_id,
                credential_definition_id=credential_definition_id
            )
            # Lastly, save the definition
            definition.save()
            return None
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def _fetch_schema(self, schema_id: str) -> Optional[str]:
        """Find a schema in Traction storage."""
        try:
            response = requests.get(self.api_url + '/schema-storage',
                                    params={'schema_id': schema_id},
                                    headers=self._get_headers())
            response.raise_for_status()
            first_or_default = next((x for x in response.json()['results'] if x['schema_id'] == schema_id), None)
            return first_or_default['schema_id'] if first_or_default else None
        except Exception as err:
            self.app.logger.error(f'Failed to fetch schema with id:{schema_id} from Traction tenant storage')
            self.app.logger.error(err)
            raise err

    @requires_traction_auth
    def _fetch_credential_definition(self, cred_def_id: str) -> Optional[str]:
        """Find a published credential definition."""
        try:
            response = requests.get(self.api_url + '/credential-definition-storage',
                                    params={'cred_def_id': cred_def_id},
                                    headers=self._get_headers())
            response.raise_for_status()
            first_or_default = next((x for x in response.json()['results'] if x['cred_def_id'] == cred_def_id), None)
            return first_or_default['cred_def_id'] if first_or_default else None
        except Exception as err:
            self.app.logger.error(f'Failed to find credential definition with id:{cred_def_id}' +
                                  ' from Traction tenant storage')
            self.app.logger.error(err)
            raise err

    @requires_traction_auth
    def create_invitation(self) -> Optional[dict]:
        """Create a new connection invitation."""
        try:
            response = requests.post(self.api_url + '/out-of-band/create-invitation',
                                     headers=self._get_headers(),
                                     params={'auto_accept': 'true'},
                                     data=json.dumps({
                                         'handshake_protocols': ['https://didcomm.org/connections/1.0']
                                     }))
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def issue_credential(self,
                         connection_id: str,
                         definition: DCDefinition,
                         data: list,  # list of { 'name': 'business_name', 'value': 'test_business' }
                         comment: str = '') -> Optional[dict]:
        """Send holder a credential, automating entire flow."""
        try:
            response = requests.post(self.api_url + '/issue-credential-2.0/send',
                                     headers=self._get_headers(),
                                     data=json.dumps({
                                         'auto_remove': 'true',
                                         'comment': comment,
                                         'connection_id': connection_id,
                                         'credential_preview': {
                                             '@type': 'issue-credential/2.0/credential-preview',
                                             'attributes': data
                                         },
                                         'filter': {
                                             'indy': {
                                                 'cred_def_id': definition.credential_definition_id,
                                                 'issuer_did': self.public_issuer_did,
                                                 'schema_id': definition.schema_id,
                                                 'schema_issuer_did': self.public_schema_did,
                                                 'schema_name': definition.schema_name,
                                                 'schema_version': definition.schema_version
                                             }
                                         },
                                         'trace': True
                                     }))
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def fetch_credential_exchange_record(self, cred_ex_id: str) -> Optional[dict]:
        """Fetch a credential exchange record."""
        try:
            response = requests.get(self.api_url + '/issue-credential-2.0/records/' + cred_ex_id,
                                    headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def revoke_credential(self, connection_id,
                          cred_rev_id: str,
                          rev_reg_id: str,
                          reason: DCRevocationReason) -> Optional[dict]:
        """Revoke a credential."""
        try:
            response = requests.post(self.api_url + '/revocation/revoke',
                                     headers=self._get_headers(),
                                     data=json.dumps({
                                         'connection_id': connection_id,
                                         'cred_rev_id': cred_rev_id,
                                         'rev_reg_id': rev_reg_id,
                                         'publish': True,
                                         'notify': True,
                                         'notify_version': 'v1_0',
                                         'comment': reason.value if reason else ''
                                     }))
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def remove_connection_record(self, connection_id: str) -> Optional[dict]:
        """Delete a connection."""
        try:
            response = requests.delete(self.api_url + '/connections/' + connection_id,
                                       headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    @requires_traction_auth
    def remove_credential_exchange_record(self, cred_ex_id: str) -> Optional[dict]:
        """Delete a credential exchange."""
        try:
            response = requests.delete(self.api_url + '/issue-credential-2.0/records/' + cred_ex_id,
                                       headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    def _get_headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.app.api_token}'
        }


class DigitalCredentialsHelpers:
    """Provides helper functions for digital credentials."""

    @staticmethod
    def get_digital_credential_data(business: Business, user: User, credential_type: DCDefinition.CredentialType):
        """Get the data for a digital credential."""
        if credential_type == DCDefinition.CredentialType.business:

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
                registered_on_dateint = business.founding_date.strftime('%Y%m%d')

            company_status = Business.State(business.state).name

            family_name = (user.lastname or '').strip().upper()

            given_names = ' '.join([x.strip() for x in [user.firstname, user.middlename] if x and x.strip()]).upper()

            # For an SP there is only one role. This will need to be updated
            # when the entity model changes and we need to support multiple roles.
            role = (
                business.party_roles[0].role if (business.party_roles and len(business.party_roles.all())) else ''
            ).replace('_', ' ').title()

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
                    'value': role or ''
                }
            ]

        return None

    @staticmethod
    def extract_invitation_message_id(json_message: dict):
        """Extract the invitation message id from the json message."""
        if 'invitation' in json_message and json_message['invitation'] is not None:
            invitation_message_id = json_message['invitation']['@id']
        else:
            invitation_message_id = json_message['invitation_msg_id']
        return invitation_message_id
