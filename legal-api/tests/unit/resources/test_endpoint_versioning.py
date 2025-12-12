# Copyright © 2021 Province of British Columbia
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
"""Test-Suite for the endpoint versioning system."""
from http import HTTPStatus
from flask import Flask

import pytest

from legal_api.resources.endpoints import endpoints


@pytest.mark.parametrize('test_name, route, test_route, expected', [
    ('v2_error', '/test_this_endpoint', '/api/v2/test_this_endpoint', HTTPStatus.NOT_FOUND),
])
def test_end_point_versioning_by_path(test_name, route, test_route, expected):
    """Test versioned endpoints by path."""
    # setup
    app = Flask(__name__)
    endpoints.app = app
    endpoints._handler_setup()
    @app.route(route)
    def index():
        return {'test': 'ok'}, HTTPStatus.OK
    
    # test by base path
    with app.test_client() as client:
        rv = client.get(test_route, follow_redirects=True)
        assert rv.status_code == expected
