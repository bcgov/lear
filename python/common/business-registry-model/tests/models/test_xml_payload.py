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

"""Tests to assure the XmlPayload Model.

Test-Suite to ensure that the XmlPayload Model is working as expected.
"""
from business_model.models import XmlPayload

def test_valid_xml_payload_save(session):
    """Assert that a valid xml payload can be saved."""
    xml_payload = XmlPayload(
        payload = '<root><element>value</element></root>',
        
    )

    xml_payload.save()
    assert xml_payload.id


def test_find_xml_payload_by_id(session):
    """Assert that the method returns correct value."""
    xml_payload = XmlPayload(
        payload='<root><element>value</element></root>'
    )

    xml_payload.save()

    res = XmlPayload.find_by_id(xml_payload_id=xml_payload.id)

    assert res
