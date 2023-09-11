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
        'schema_name': 'digital_business_card', # do not change schema name. this is the name registered in aca-py agent
        'schema_version': '1.0.0' # if attributes changes update schema_version to re-register
    }

    def __init__(self):
        """Initialize this object."""
        self.app = None

        self.api_url = None
        self.api_token = None
        self.public_did = None

    def init_app(self, app):
        """Initialize digital credentials using aca-py agent."""
        self.app = app

        self.api_url = app.config.get('TRACTION_API_URL')
        self.api_token = app.config.get('TRACTION_API_TOKEN')
        self.public_did = app.config.get('TRACTION_PUBLIC_DID')
        with suppress(Exception):
            self._register_business_definition()

    def _register_business_definition(self):
        """Publish Business schema and credential definition and save a Business definition."""
        # check for the current Business definition.
        definition = DCDefinition.find_by(
            credential_type=DCDefinition.CredentialType.business,
            schema_name=self.business_schema['schema_name'],
            schema_version=self.business_schema['schema_version']
        )

        if definition and not definition.is_deleted:
            # deactivate any existing Business definition before creating new one
            DCDefinition.deactivate(DCDefinition.CredentialType.business)

        # look for a published schema first, if it's not there then register one.
        schema_id = self._get_schema(self.business_schema) # TODO: This should look up the last updated definition in Traction storage
        if not schema_id:
            schema_id = self._publish_schema(self.business_schema)

        # create a new definition and add the new schema_id
        definition = DCDefinition(
            credential_type=DCDefinition.CredentialType.business,
            schema_name=self.business_schema['schema_name'],
            schema_version=self.business_schema['schema_version'],
            schema_id=schema_id
        )

        # look for a published credential definition first, if it's not there then register one.
        if not definition.credential_definition_id:
            schema_id = definition.schema_id
            credential_definition_id = self._get_credential_definition(schema_id) # TODO: this should look up the last updated credential definition in Traction storage
            if not credential_definition_id:
                credential_definition_id = self._publish_credential_definition(schema_id)

        # add the new credential_definition_id
        definition.credential_definition_id = credential_definition_id

        # lastly, save the definition    
        definition.save()

    def _get_schema(self, schema: dict) -> Optional[str]:
        """Find a published schema"""
        try:
            response = requests.get(self.api_url + '/schemas/created',
                                    params={'schema_name': schema['schema_name'],
                                            'schema_version': schema['schema_version']},
                                    headers=self._get_headers())
            response.raise_for_status()
            return response.json()['schema_ids'][0]
        except Exception as err:
            self.app.logger.error(
                f"Failed to find digital credential schema {schema['schema_name']}:{schema['schema_version']}")
            self.app.logger.error(err)
            raise err

    def _publish_schema(self, schema: dict) -> Optional[str]:
        """Publish a schema onto the ledger."""
        try:
            response = requests.post(self.api_url + '/schemas',
                                     headers=self._get_headers(),
                                     data=json.dumps(schema))
            response.raise_for_status()
            return response.json()[0]['schema_id']
        except Exception as err:
            self.app.logger.error(
                f"Failed to register digital credential schema {schema['schema_name']}:{schema['schema_version']}")
            self.app.logger.error(err)
            raise err
        
    def _get_credential_definition(self, schema_id: str) -> Optional[str]:
        """Find a published credential definition"""
        try:
            response = requests.get(self.api_url + '/credential-definitions/created',
                                    params={'schema_id': schema_id},
                                    headers=self._get_headers())
            response.raise_for_status()
            return response.json()['credential_definition_ids'][0]
        except Exception as err:
            self.app.logger.error(f'Failed to find credential definition with schema_id:{schema_id}')
            self.app.logger.error(err)
            raise err

    def _publish_credential_definition(self, schema_id: str) -> Optional[str]:
        """Publish a credential definition onto the ledger."""
        try:
            response = requests.post(self.api_url + '/credential-definitions',
                                     headers=self._get_headers(),
                                     data=json.dumps({
                                        #  'revocation_registry_size': 1000,
                                         'schema_id': schema_id,
                                         'support_revocation': False,
                                         'tag': 'DigitalBusinessCard'
                                     }))
            response.raise_for_status()
            return response.json()['credential_definition_id']
        except Exception as err:
            self.app.logger.error(f'Failed to register credential definition schema_id:{schema_id}')
            self.app.logger.error(err)
            raise err

    def create_invitation(self) -> Optional[dict]:
        """Create a new connection invitation."""
        try:
            response = requests.post(self.api_url + '/connections/create-invitation',
                                     headers=self._get_headers(),
                                     data={})
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
            response = requests.post(self.api_url + '/issue-credential/send',
                                     headers=self._get_headers(),
                                     data=json.dumps({
                                         'auto_remove': True,
                                         'comment': comment,
                                         'connection_id': connection_id,
                                         'cred_def_id': definition.credential_definition_id,
                                         'credential_proposal': {
                                             '@type': 'issue-credential/1.0/credential-preview',
                                             'attributes': data
                                         },
                                         'issuer_did': self.public_did,
                                         'schema_id': definition.schema_id,
                                         'schema_issuer_did': self.public_did,
                                         'schema_name': definition.schema_name,
                                         'schema_version': definition.schema_version,
                                         'trace': True
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
