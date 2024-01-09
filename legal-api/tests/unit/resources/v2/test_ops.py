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


def test_ops_healthz_success(client):
    """Assert that the service is healthy if it can successfully access the database."""
    rv = client.get("/ops/healthz")

    assert rv.status_code == 200
    assert rv.json == {"message": "api is healthy"}


def test_ops_healthz_fail(app_request):
    """Assert that the service is unhealthy if a connection toThe database cannot be made."""
    app_request.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://does:not@exist:5432/nada"
    with app_request.test_client() as client:
        rv = client.get("/ops/healthz")

        assert rv.status_code == 500
        assert rv.json == {"message": "api is down"}


def test_ops_readyz(client):
    """Asserts that the service is ready to serve."""
    rv = client.get("/ops/readyz")

    assert rv.status_code == 200
    assert rv.json == {"message": "api is ready"}
