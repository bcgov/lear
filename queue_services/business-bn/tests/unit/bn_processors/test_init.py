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
    ({"street": "123 Main St"}, {"street": "123 Main St"}),
    ({"street": "123 #456 Main St"}, {"street": "123 456 Main St"}),
    ({"street": "Line 1\nLine 2"}, {"street": "Line 1 Line 2"}),
    ({"street": "Line 1\rLine 2"}, {"street": "Line 1 Line 2"}),
    ({"street": "123 #456\nMain St"}, {"street": "123 456 Main St"}),
    ({"street": "#Start"}, {"street": "Start"}),
    ({"street": "End#"}, {"street": "End"}),
    ({"street": "#\n\r"}, {"street": ""}),
])
def test_cleanse_address(test_input, expected):
    """Test the _cleanse_address function."""
    assert sanitize_address(test_input) == expected


def test_cleanse_address_mutation():
    """Test that _cleanse_address modifies dictionary in place (or returns modified copy effectively)."""
    # Note: Current implementation modifies in place.
    address = {"street": "123 #456"}
    cleaned = sanitize_address(address)
    assert cleaned["street"] == "123 456"
    assert address["street"] == "123 456"
