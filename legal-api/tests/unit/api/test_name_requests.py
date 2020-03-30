# Copyright © 2020 Province of British Columbia
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

from http import HTTPStatus

"""Tests to assure the name requests end-point.

Test-Suite to ensure that the /nameRequests endpoint is working as expected.
"""


def test_name_requests_success(client):
    """Assert that a name request can be received."""
    rv = client.get('/api/v1/nameRequests/NR 3252362')

    assert rv.status_code == HTTPStatus.OK
    assert 'nrNum' in rv.json
    assert rv.json['nrNum'] == 'NR 3252362'


def test_name_requests_not_found(client):
    """Assert that a name request can be received."""
    rv = client.get('/api/v1/nameRequests/NR 1234567')

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': 'NR 1234567 not found.'}
