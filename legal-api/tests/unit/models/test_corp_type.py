# Copyright © 2021 Province of British Columbia
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

"""Tests to assure the CorpType Model.

Test-Suite to ensure that the CorpType Model is working as expected.
"""

from legal_api.models import LegalEntity, CorpType


corp_type_json = {
    'corp_type_cd': 'BEN',
    'colin_ind': 'Y',
    'corp_class': 'BC',
    'short_desc': 'BENEFIT COMPANY',
    'full_desc': 'BC Benefit Company',
    'legislation': 'BC Business Corporations Act'
}


def test_corp_type_json(session):
    """Assert the json format of corp type."""
    corp_type = CorpType.find_by_id(LegalEntity.EntityTypes.BCOMP.value)
    assert corp_type_json == corp_type.json


def test_find_corp_type_by_id(session):
    """Assert that the method returns the corp type matching the id."""
    corp_type = CorpType.find_by_id(LegalEntity.EntityTypes.BCOMP.value)

    assert corp_type
    assert corp_type_json == corp_type.json


def test_find_all(session):
    """Assert that the method returns all corp types."""
    corp_types = CorpType.find_all()
    entity_types = [key for key in LegalEntity.EntityTypes if key.name not in (LegalEntity.EntityTypes.PERSON.name,
                                                                               LegalEntity.EntityTypes.ORGANIZATION.name)]
    assert len(corp_types) == len(entity_types)
    assert all(corp_type.corp_type_cd in LegalEntity.EntityTypes._value2member_map_ for corp_type in corp_types)
