# Copyright © 2023 Province of British Columbia
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

"""Tests to assure the AlternateName Model.

Test-Suite to ensure that the AlternateName Model is working as expected.
"""
from datetime import datetime

from business_model import AlternateName
from tests.models import factory_legal_entity


def test_valid_alternate_name_save(session):
    """Assert that a valid alias can be saved."""
    identifier = 'BC1234567'
    legal_entity = factory_legal_entity(identifier)

    alternate_name_1 = AlternateName(
        identifier=identifier,
        name_type=AlternateName.NameType.OPERATING,
        name='XYZ Test BC LTD',
        bn15='111111100BC1111',
        start_date=datetime.utcnow(),
        legal_entity_id=legal_entity.id,
    )
    alternate_name_1.save()

    alternate_name_2 = AlternateName(
        identifier=identifier,
        name_type=AlternateName.NameType.OPERATING,
        name='ABC Test BC LTD',
        bn15='222222200BC2222',
        start_date=datetime.utcnow(),
        legal_entity_id=legal_entity.id,
    )
    alternate_name_2.save()

    # verify
    assert alternate_name_1.id
    assert alternate_name_2.id
    alternate_names = legal_entity.alternate_names.all()
    assert len(alternate_names) == 2
    assert all(alternate_name.name_type == AlternateName.NameType.OPERATING for alternate_name in alternate_names)
    assert any(alternate_name.name == 'XYZ Test BC LTD' for alternate_name in alternate_names)
    assert any(alternate_name.name == 'ABC Test BC LTD' for alternate_name in alternate_names)

