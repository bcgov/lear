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
"""Test the core/Business services."""
import re

import pytest

from legal_api.core.business import BusinessIdentifier, BusinessType


@pytest.mark.parametrize('business_type,expected',[
    (BusinessType.COOPERATIVE, True),
    ('NOT_FOUND', False),
])
def test_business_next_identifier(session, business_type, expected):
    """Assert that the next identifier is correctly generated."""
    identifier = BusinessIdentifier.next_identifier(business_type)

    if expected:
        legal_type = identifier[:re.search(r"\d", identifier).start()]
        assert legal_type in BusinessType
        assert identifier[identifier.find(legal_type) + len(legal_type):].isdigit()
    else:
        assert identifier is None

def test_get_enum_by_value():
    """Assert that the get_enum_by_value function returns the correct enum."""
    assert BusinessType.get_enum_by_value('CP') == BusinessType.COOPERATIVE
    assert BusinessType.get_enum_by_value('NOT_FOUND') is None
