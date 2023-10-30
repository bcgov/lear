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

"""Tests to assure the DCIssuedCredential Model.

Test-Suite to ensure that the DCIssuedCredential Model is working as expected.
"""
import uuid

from business_model import DCIssuedCredential

from tests.models import factory_legal_entity
from tests.models.test_dc_connection import create_dc_connection
from tests.models.test_dc_definition import create_dc_definition


def test_valid_dc_issued_credential_save(session):
    """Assert that a valid dc_issued_credential can be saved."""
    issued_credential = create_dc_issued_credential()
    assert issued_credential.id


def test_find_by_id(session):
    """Assert that the method returns correct value."""
    issued_credential = create_dc_issued_credential()
    res = DCIssuedCredential.find_by_id(issued_credential.id)
    assert res


def test_find_by_credential_exchange_id(session):
    """Assert that the method returns correct value."""
    issued_credential = create_dc_issued_credential()
    res = DCIssuedCredential.find_by_credential_exchange_id(issued_credential.credential_exchange_id)

    assert res
    assert res.id == issued_credential.id


def test_find_by(session):
    """Assert that the method returns correct value."""
    issued_credential = create_dc_issued_credential()
    res = DCIssuedCredential.find_by(dc_connection_id=issued_credential.dc_connection_id,
                                     dc_definition_id=issued_credential.dc_definition_id)

    assert len(res) == 1
    assert res[0].id == issued_credential.id


def create_dc_issued_credential(legal_entity=None):
    """Create new dc_issued_credential object."""
    if not legal_entity:
        identifier = 'FM1234567'
        legal_entity =factory_legal_entity(identifier)
    definition = create_dc_definition()
    connection = create_dc_connection(legal_entity, is_active=True)
    issued_credential = DCIssuedCredential(
        dc_definition_id=definition.id,
        dc_connection_id=connection.id,
        credential_exchange_id=str(uuid.uuid4())
    )
    issued_credential.save()
    return issued_credential