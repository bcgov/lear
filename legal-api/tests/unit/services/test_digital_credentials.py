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
"""Tests for the Minio service.

Test suite to ensure that the Digital Credentials service are working as expected.
"""
from unittest.mock import patch

from legal_api.models import DCDefinition
from legal_api.services import digital_credentials
from legal_api.services.digital_credentials import DigitalCredentialsService


def test_init_app(session, app):  # pylint:disable=unused-argument
    """Assert that the init app register schema and credential definition."""
    schema_id = '3ENKbWGgUBXXzDHnG11phS:2:business_schema:1.0.0'
    cred_def_id = '3ENKbWGgUBXXzDHnG11phS:3:CL:146949:business_schema'
    with patch.object(DigitalCredentialsService, '_register_schema', return_value=schema_id):
        with patch.object(DigitalCredentialsService, '_register_credential_definitions', return_value=cred_def_id):
            digital_credentials.init_app(app)
            definition = DCDefinition.find_by_credential_type(DCDefinition.CredentialType.business)
            assert definition.schema_id == schema_id
            assert definition.schema_name == digital_credentials.business_schema['schema_name']
            assert definition.schema_version == digital_credentials.business_schema['schema_version']
            assert definition.credential_definition_id == cred_def_id
            assert not definition.is_deleted
