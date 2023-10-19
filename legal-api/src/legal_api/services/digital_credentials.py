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

from legal_api.models import DCDefinition


class DigitalCredentialsService:
    """Provides services to do digital credentials using aca-py agent."""

    business_schema = {
        'attributes': [
            'business_name',
            'company_status',
            'credential_id',
            'identifier',
            'registered_on_dateint',
            'role',
            'cra_business_number',
            'family_name',
            'business_type',
            'given_names',
        ],
        # do not change schema name. this is the name registered in aca-py agent
        'schema_name': 'digital_business_card',
        # if attributes change update schema_version to re-register
        'schema_version': '1.0.0'
    }

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
        self.api_token = app.config.get('TRACTION_API_TOKEN')
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
            if self.business_schema_id is None:
                self.app.logger.error('Environment variable: BUSINESS_SCHEMA_ID must be configured')
                raise ValueError('Environment variable: BUSINESS_SCHEMA_ID must be configured')

            if self.business_cred_def_id is None:
                self.app.logger.error('Environment variable: BUSINESS_CRED_DEF_ID must be configured')
                raise ValueError('Environment variable: BUSINESS_CRED_DEF_ID must be configured')

            # Check for the current Business definition.
            definition = DCDefinition.find_by(
                credential_type=DCDefinition.CredentialType.business,
                schema_id=self.business_schema_id,
                credential_definition_id=self.business_cred_def_id
            )

            if definition and not definition.is_deleted:
                # Deactivate any existing Business definition before creating new one
                DCDefinition.deactivate(DCDefinition.CredentialType.business)

            ###
            # The following just a sanity check to make sure the schema and
            # credential definition are stored in Traction tenant.
            # These calls also include a ledger lookup to see if the schema
            # and credential definition are published.
            ###

            # Look for a schema first, and copy it into the Traction tenant if it's not there
            schema_id = self._fetch_schema(self.business_schema_id)
            if not schema_id:
                raise ValueError(f'Schema with id:{self.business_schema_id}' +
                                 ' must be available in Traction tenant storage')

            # Look for a published credential definition first, and copy it into the Traction tenant if it's not there
            credential_definition_id = self._fetch_credential_definition(self.business_cred_def_id)
            if not credential_definition_id:
                raise ValueError(f'Credential Definition with id:{self.business_cred_def_id}' +
                                 ' must be avaible in Traction tenant storage')

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

    def revoke_credential(self, connection_id, cred_rev_id: str, rev_reg_id: str) -> Optional[dict]:
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
                                         'notify_version': 'v1_0'
                                     }))
            response.raise_for_status()
            return response.json()
        except Exception as err:
            self.app.logger.error(err)
            return None

    def _get_headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_token}'
        }
