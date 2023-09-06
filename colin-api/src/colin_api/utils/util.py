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

"""CORS pre-flight decorator.

A simple decorator to add the options method to a Request Class.
"""
from functools import wraps

from legal_api.services import flags


def cors_preflight(methods: str = 'GET'):
    """Render an option method on the class."""
    def wrapper(f):
        def options(self, *args, **kwargs):  # pylint: disable=unused-argument
            return {'Allow': 'GET'}, 200, \
                   {'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': methods,
                    'Access-Control-Allow-Headers': 'Authorization, Content-Type'}

        setattr(f, 'options', options)
        return f
    return wrapper


def conditional_auth(auth_decorator, roles):
    """Authenticate an endpoint conditionally based off of the value of disable-colin-api-auth feature flag value.

    When disable-colin-api-auth feature flag value is True, auth_decorator function will not be called resulting in
    the endpoint using this decorator to run without authentication.

    When disable-colin-api-auth feature flag value is False, auth_decorator function will be called resulting in
    the endpoint using this decorator to authenticate the api consumer.  In this scenario, the REST resource(endpoint)
    should be decorated with "@conditional_auth(jwt.requires_roles, [COLIN_SVC_ROLE])".
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            auth_is_disabled = flags.is_on('disable-colin-api-auth')

            if auth_is_disabled:  # pylint: disable=R1705;
                return f(*args, **kwargs)
            else:
                return auth_decorator(roles)(f)(*args, **kwargs)

        return wrapped

    return decorator
