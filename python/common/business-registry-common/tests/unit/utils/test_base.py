# Copyright © 2025 Province of British Columbia
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
"""Tests for BaseEnum and BaseMeta utilities."""
from business_common.utils.base import BaseEnum


class SampleEnum(BaseEnum):
    """Sample enum for testing."""

    FOO = "foo"
    BAR = "bar"


def test_get_enum_by_value():
    """Assert get_enum_by_value returns the member or None."""
    assert SampleEnum.get_enum_by_value("foo") == SampleEnum.FOO
    assert SampleEnum.get_enum_by_value("bar") == SampleEnum.BAR
    assert SampleEnum.get_enum_by_value("unknown") is None


def test_base_meta_contains():
    """Assert 'in' operator works for valid and invalid values."""
    assert "foo" in SampleEnum
    assert "unknown" not in SampleEnum
    assert SampleEnum.FOO == "foo"
