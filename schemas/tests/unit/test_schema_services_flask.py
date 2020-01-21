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
"""Test Suite to validate the Flask extension to manage the cached schemas.

Flask extension to validate json data against the JSONSchema's that have been cached.
"""
from flask import Flask, g

from registry_schemas.example_data import ANNUAL_REPORT
from registry_schemas.flask import SchemaServices

from .schema_data import TEST_SCHEMAS_DATA


def create_app():
    """Create a flask app instance in TEST mode."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_cache_is_setup():
    """Assert that the services cache is setup."""
    app = create_app()
    schema_service = SchemaServices()
    with app.app_context():
        schema_service.init_app(app)

        schema_store = schema_service.rsbc_filing_schema_store

        assert schema_store

        assert len(schema_store) == len(TEST_SCHEMAS_DATA)


def test_cache_is_setup_inline_app_init():
    """Assert that the cache is setup, with the service being bound to Flask on creation."""
    app = create_app()
    with app.app_context():
        schema_service = SchemaServices(app)

        schema_store = schema_service.rsbc_filing_schema_store

        assert schema_store

        assert len(schema_store) == len(TEST_SCHEMAS_DATA)


def test_ensure_cache_used():
    """Assert that the cache in the service is being used and not recreated at every call."""
    import copy

    app = create_app()
    with app.app_context():
        schema_service = SchemaServices(app)

        schema_store = schema_service.rsbc_filing_schema_store
        store = copy.deepcopy(schema_store)

        schema_store.popitem()

        schema_store = schema_service.rsbc_filing_schema_store

        assert len(schema_store) == len(store) - 1


def test_service_teardown():
    """Assert that the service is torn down correctly."""
    app = create_app()
    with app.app_context():
        schema_service = SchemaServices(app)
        schema_store = schema_service.rsbc_filing_schema_store
        schema_service.teardown(None)
        assert schema_store == {}


def test_service_teardown_store_missing():
    """Assert the store is not torn down if removed fromThe global flask context."""
    app = create_app()
    with app.app_context():
        schema_service = SchemaServices(app)
        schema_store = schema_service.rsbc_filing_schema_store

        g.pop('rsbc_filing_schema_store', None)
        schema_service.teardown(None)
        assert schema_store


def test_validate():
    """Assert that a valid AR can be validated against the JSON Schemas in the store."""
    app = create_app()
    schema_service = SchemaServices()
    with app.app_context():
        schema_service.init_app(app)

        valid, _ = schema_service.validate(ANNUAL_REPORT, 'filing')

        assert valid
