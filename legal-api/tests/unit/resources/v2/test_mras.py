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

"""Tests to assure the MRAS end-point.

Test-Suite to ensure that mras endpoints are working as expected.
"""
from http import HTTPStatus

from legal_api.models import UserRoles
from tests.unit.services.utils import create_header


def test_get_jurisdictions(session, client, jwt):
    """Assert that the endpoint returns foreign jurisdiction information."""
    rv = client.get('/api/v2/mras/BC1234567',
                    headers=create_header(jwt, [UserRoles.system]))

    assert rv.status_code == HTTPStatus.OK
    assert 'jurisdictions' in rv.json
    assert rv.json['jurisdictions'] == []


def test_get_jurisdictions_invalid_role(session, client, jwt):
    """Assert that the endpoint validates invalid user role."""
    rv = client.get('/api/v2/mras/BC1234567',
                    headers=create_header(jwt, [UserRoles.basic]))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED
