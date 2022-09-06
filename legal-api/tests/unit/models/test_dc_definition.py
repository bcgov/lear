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

"""Tests to assure the DCDefinition Model.

Test-Suite to ensure that the DCDefinition Model is working as expected.
"""

from legal_api.models import DCDefinition
from legal_api.services import digital_credentials


def test_valid_dc_definition_save(session):
    """Assert that a valid dc_definition can be saved."""
    definition = create_dc_definition()
    assert definition.id


def test_find_by_id(session):
    """Assert that the method returns correct value."""
    definition = create_dc_definition()

    res = DCDefinition.find_by_id(definition.id)

    assert res
    assert res.schema_id == definition.schema_id
    assert not res.is_deleted


def test_find_by_credential_type(session):
    """Assert that the method returns correct value."""
    definition = create_dc_definition()

    res = DCDefinition.find_by_credential_type(DCDefinition.CredentialType.business)

    assert res
    assert res.schema_id == definition.schema_id


def test_deactivate(session):
    """Assert that the deactivate set is_deleted value."""
    definition = create_dc_definition()

    DCDefinition.deactivate(DCDefinition.CredentialType.business)

    res = DCDefinition.find_by_id(definition.id)
    assert res.is_deleted

    res = DCDefinition.find_by_credential_type(DCDefinition.CredentialType.business)
    assert not res


def test_find_by(session):
    """Assert that the method returns correct value."""
    definition = create_dc_definition()

    res = DCDefinition.find_by(DCDefinition.CredentialType.business,
                               digital_credentials.business_schema['schema_name'],
                               schema_version=digital_credentials.business_schema['schema_version']
                               )
    assert len(res) == 1
    assert res[0].id == definition.id


def create_dc_definition():
    """Create new dc_definition object."""
    definition = DCDefinition(
        credential_type=DCDefinition.CredentialType.business,
        schema_name=digital_credentials.business_schema['schema_name'],
        schema_version=digital_credentials.business_schema['schema_version'],
        schema_id='3ENKbWGgUBXXzDHnG11phS:2:business_schema:1.0.0',
        credential_definition_id='3ENKbWGgUBXXzDHnG11phS:3:CL:146949:business_schema'
    )
    definition.save()
    return definition
