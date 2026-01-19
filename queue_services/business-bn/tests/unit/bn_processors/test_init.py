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
"""The Test Suites to ensure the bn_processors init helper functions are working correctly."""
import pytest
from business_bn.bn_processors import sanitize_address


@pytest.mark.parametrize("test_input, expected", [
    (None, None),
    ({}, {}),
    ({"streetAddress": "123 Main St"}, {"streetAddress": "123 Main St"}),
    ({"streetAddress": "123 #456 Main St"}, {"streetAddress": "123 456 Main St"}),
    ({"streetAddress": "Line 1\nLine 2"}, {"streetAddress": "Line 1 Line 2"}),
    ({"streetAddress": "Line 1\rLine 2"}, {"streetAddress": "Line 1 Line 2"}),
    ({"streetAddress": "123 #456\nMain St"}, {"streetAddress": "123 456 Main St"}),
    ({"streetAddress": "#Start"}, {"streetAddress": "Start"}),
    ({"streetAddress": "End#"}, {"streetAddress": "End"}),
    ({"streetAddress": "#\n\r"}, {"streetAddress": ""}),
    # French characters
    ({"streetAddress": "Montréal"}, {"streetAddress": "Montréal"}),
    ({"streetAddress": "François"}, {"streetAddress": "François"}),
    ({"streetAddress": "L'Ancienne-Lorette"}, {"streetAddress": "L Ancienne Lorette"}),
    # Indigenous characters
    ({"streetAddress": "T’Sou-ke"}, {"streetAddress": "T Sou ke"}),
    ({"streetAddress": "Šxʷwəq̓ʷəθət"}, {"streetAddress": "Šxʷwəq̓ʷəθət"}),
])
def test_cleanse_address(test_input, expected):
    """Test the _cleanse_address function."""
    assert sanitize_address(test_input) == expected


def test_cleanse_address_mutation():
    """Test that _cleanse_address modifies dictionary in place (or returns modified copy effectively)."""
    # Note: Current implementation modifies in place.
    address = {"streetAddress": "123 #456"}
    cleaned = sanitize_address(address)
    assert cleaned["streetAddress"] == "123 456"
    assert address["streetAddress"] == "123 456"
