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

"""Tests to assure the ops end-point.

Test-Suite to ensure that the /ops endpoint is working as expected.
"""
from tests import oracle_integration


@oracle_integration
def test_ops_healthz_success(client):
    """Assert that the service is healthy if it can successfully access the database."""
    rv = client.get('/ops/healthz')

    assert 200 == rv.status_code
    assert {'message': 'api is healthy'} == rv.json


def test_ops_healthz_fail(app_request):
    """Assert that the service is unhealthy if a connection toThe database cannot be made."""
    app_request.config['ORACLE_DB_NAME'] = 'somethingnotreal'
    with app_request.test_client() as client:
        rv = client.get('/ops/healthz')

        assert 500 == rv.status_code
        assert 'api is down' in rv.json.values()


def test_ops_readyz(client):
    """Asserts that the service is ready to serve."""
    rv = client.get('/ops/readyz')

    assert 200 == rv.status_code
    assert {'message': 'api is ready'} == rv.json
