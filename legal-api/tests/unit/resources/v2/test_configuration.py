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

"""Tests to assure the configuration end-point.

Test-Suite to ensure that admin/configuration endpoints are working as expected.
"""
from http import HTTPStatus

from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from tests.unit.services.utils import create_header


def test_get_configurations(app, session, client, jwt):
    """Assert that get results are returned."""

    # test
    rv = client.get(f'/api/v2/admin/configurations',
                    headers=create_header(jwt, [STAFF_ROLE], 'user'))

    # check
    assert rv.status_code == HTTPStatus.OK
    assert 'configurations' in rv.json
    results = rv.json['configurations']
    assert len(results) == 4

    names = {'NUM_DISSOLUTIONS_ALLOWED', 'MAX_DISSOLUTIONS_ALLOWED', 'DISSOLUTIONS_ON_HOLD', 'NEW_DISSOLUTIONS_SCHEDULE'}
    for res in results:
        assert res['name'] in names


def test_get_configurations_with_invalid_user(app, session, client, jwt):
    """Assert that is unauthorized."""

    # test
    rv = client.get(f'/api/v2/admin/configurations',
                    headers=create_header(jwt, [BASIC_USER], 'user'))

    # check
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
