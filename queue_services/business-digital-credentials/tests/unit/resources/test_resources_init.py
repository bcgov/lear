# Copyright © 2025 Province of British Columbia
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
"""Test the resources init module."""
from flask import Flask

from business_digital_credentials.resources import register_endpoints


def test_register_endpoints():
    """Test that endpoints are registered properly."""
    app = Flask(__name__)

    assert len(app.blueprints) == 0

    register_endpoints(app)

    assert len(app.blueprints) == 2
    assert "worker" in app.blueprints
    assert "ops" in app.blueprints
    assert app.url_map.strict_slashes is False


def test_register_endpoints_with_ops():
    """Test that ops endpoint is also registered."""
    app = Flask(__name__)

    register_endpoints(app)

    blueprint_names = list(app.blueprints.keys())
    
    assert "worker" in blueprint_names
    assert "ops" in blueprint_names
    
    ops_blueprint = app.blueprints["ops"]
    worker_blueprint = app.blueprints["worker"]
    assert ops_blueprint is not None
    assert worker_blueprint is not None
