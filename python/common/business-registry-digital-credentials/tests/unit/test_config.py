# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for config module."""

import pytest
from business_registry_digital_credentials.config import DevConfig, ProdConfig, TestConfig, get_named_config


@pytest.mark.parametrize(
    "name, expected_type",
    [
        ("production", ProdConfig),
        ("staging", ProdConfig),
        ("default", ProdConfig),
        ("testing", TestConfig),
        ("development", DevConfig),
    ],
)
def test_get_named_config(name, expected_type):
    assert isinstance(get_named_config(name), expected_type)


def test_get_named_config_unknown():
    with pytest.raises(KeyError):
        get_named_config("unknown")
