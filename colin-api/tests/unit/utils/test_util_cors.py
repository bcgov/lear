# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the CORS utilities.

Test-Suite to ensure that the CORS decorator is working as expected.
"""
import pytest

from colin_api.utils.util import cors_preflight


TEST_CORS_METHODS_DATA = [
    ('GET'),
    ('PUT'),
    ('POST'),
    ('GET,PUT'),
    ('GET,POST'),
    ('PUT,POST'),
    ('GET,PUT,POST'),
]


@pytest.mark.parametrize('methods', TEST_CORS_METHODS_DATA)
def test_cors_preflight_post(methods):
    """Assert that the options methos is added to the class and that the correct access controls are set."""
    @cors_preflight(methods)  # pylint: disable=too-few-public-methods
    class TestCors():
        pass

    rv = TestCors().options()  # pylint: disable=no-member

    assert rv[2]['Access-Control-Allow-Origin'] == '*'
    assert rv[2]['Access-Control-Allow-Methods'] == methods
    assert rv[2]['Access-Control-Allow-Headers'] == 'Authorization, Content-Type, App-Name'
