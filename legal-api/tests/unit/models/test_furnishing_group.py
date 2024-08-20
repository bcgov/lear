# Copyright © 2024 Province of British Columbia
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

"""Tests to assure the Furnishing Group Model.

Test-Suite to ensure that the Furnishing Group Model is working as expected.
"""
from legal_api.models import FurnishingGroup, XmlPayload

def test_valid_furnishing_save(session):
    """Assert that a valid furnishing_group can be saved."""
    xml_payload = XmlPayload(
        payload = '<root><element>value</element></root>',
        
    )
    xml_payload.save()

    furnishing_group = FurnishingGroup(
        xml_payload_id = xml_payload.id
    )

    furnishing_group.save()
    assert furnishing_group.id


def test_find_furnishing_group_by_id(session):
    """Assert that the method returns correct value."""
    xml_payload = XmlPayload(
        payload = '<root><element>value</element></root>',
        
    )
    xml_payload.save()

    furnishing_group = FurnishingGroup(
        xml_payload_id = xml_payload.id
    )
    furnishing_group.save()

    res = FurnishingGroup.find_by_id(furnishing_group_id=furnishing_group.id)
    assert res


def test_find_furnishing_group_by(session):
    """Assert that the method returns correct values."""
    xml_payload = XmlPayload(
        payload = '<root><element>value</element></root>',
        
    )
    xml_payload.save()

    furnishing_group = FurnishingGroup(
        xml_payload_id = xml_payload.id
    )
    furnishing_group.save()

    res = FurnishingGroup.find_by(xml_payload_id=xml_payload.id)

    assert len(res) == 1
    assert res[0].id == furnishing_group.id
