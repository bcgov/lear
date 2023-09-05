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

"""Test-Suite to ensure that the conditional_auth works as expected."""
from functools import wraps
from unittest.mock import patch
from colin_api.utils.util import conditional_auth

# Mock function to be decorated
def mock_end_point_func(*args, **kwargs):
    return "Endpoint Function"


# Mock auth decorator
def mock_auth_decorator(roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            return "Auth Decorated: " + f(*args, **kwargs)
        return wrapped
    return decorator


def test_auth_enabled_executes_auth_decorator(app):
    """Assert that a mock endpoint using conditional_auth invokes the auth decorator(mock_auth_decorator)
       when colin api auth is turned on(disable-colin-api-auth = False)."""
    with patch('colin_api.utils.util.flags.is_on', return_value=False):
        decorated = conditional_auth(mock_auth_decorator, ["role1"])(mock_end_point_func)
        result = decorated()
        assert result == "Auth Decorated: Endpoint Function"  # Check that auth_decorator logic was executed


def test_auth_disabled_skips_auth_decorator(app):
    """Assert that a mock endpoint using conditional_auth does not invoke the auth decorator(mock_auth_decorator)
       when colin api auth is turned off(disable-colin-api-auth = True)."""
    with patch('colin_api.utils.util.flags.is_on', return_value=True):
        decorated = conditional_auth(mock_auth_decorator, ["role1"])(mock_end_point_func)
        result = decorated()
        assert result == "Endpoint Function"  # Check that auth_decorator logic was executed
