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

    res = DCDefinition.find_by(credential_type=DCDefinition.CredentialType.business,
                               schema_id='test_schema_id',
                               credential_definition_id='test_credential_definition_id',
                               )
    assert res
    assert res.id == definition.id


def create_dc_definition():
    """Create new dc_definition object."""
    definition = DCDefinition(
        credential_type=DCDefinition.CredentialType.business,
        schema_name='test_business_schema',
        schema_version='1.0.0',
        schema_id='test_schema_id',
        credential_definition_id='test_credential_definition_id'
    )
    definition.save()
    return definition
