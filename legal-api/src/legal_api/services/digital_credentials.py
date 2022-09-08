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
            'legalName',
            'foundingDate',
            'taxId',
            'homeJurisdiction',
            'legalType',
            'identifier'
        ],
        'schema_name': 'business_schema',  # do not change schema name. this is the name registered in agent
        'schema_version': '1.0.0'  # if attributes changes update schema_version to re-register
    }

    def __init__(self):
        """Initialize this object."""
        self.app = None

        self.api_url = None
        self.api_key = None
        self.entity_did = None

    def init_app(self, app):
        """Initialize digital credentials using aca-py agent."""
        self.app = app

        self.api_url = app.config.get('ACA_PY_ADMIN_API_URL')
        self.api_key = app.config.get('ACA_PY_ADMIN_API_KEY')
        self.entity_did = app.config.get('ACA_PY_ENTITY_DID')
        with suppress(Exception):
            self._register_business()

    def _register_business(self):
        """Register business schema and credential definition."""
        # check for the current schema definition.
        definition = DCDefinition.find_by(
            credential_type=DCDefinition.CredentialType.business,
            schema_name=self.business_schema['schema_name'],
            schema_version=self.business_schema['schema_version']
        )

        if definition:
            if definition.is_deleted:
                raise Exception('Digital Credentials: business_schema is marked as delete, fix it.')
        else:
            # deactivate any existing schema definition before registering new one
            DCDefinition.deactivate(DCDefinition.CredentialType.business)

            schema_id = self._register_schema(self.business_schema)
            definition = DCDefinition(
                credential_type=DCDefinition.CredentialType.business,
                schema_name=self.business_schema['schema_name'],
                schema_version=self.business_schema['schema_version'],
                schema_id=schema_id
            )
            definition.save()

        if not definition.credential_definition_id:
            definition.credential_definition_id = self._register_credential_definitions(definition.schema_id)
            definition.save()

    def _register_schema(self, schema: dict) -> Optional[str]:
        """Send a schema to the ledger."""
        try:
            response = requests.post(self.api_url + '/schemas',
                                     headers=self._get_headers(),
                                     data=json.dumps(schema))
            response.raise_for_status()
            return response.json()['schema_id']
        except Exception as err:
            self.app.logger.error(
                f"Failed to register digital credential schema {schema['schema_name']}:{schema['schema_version']}")
            self.app.logger.error(err)
            raise err

    def _register_credential_definitions(self, schema_id: str) -> Optional[str]:
        """Send a credential definition to the ledger."""
        try:
            response = requests.post(self.api_url + '/credential-definitions',
                                     headers=self._get_headers(),
                                     data=json.dumps({
                                         'revocation_registry_size': 1000,
                                         'schema_id': schema_id,
                                         'support_revocation': True,
                                         'tag': 'business_schema'
                                     }))
            response.raise_for_status()
            return response.json()['credential_definition_id']
        except Exception as err:
            self.app.logger.error(f'Failed to register credential definition schema_id:{schema_id}')
            self.app.logger.error(err)
            raise err

    def _get_headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'X-API-KEY': self.api_key
        }
