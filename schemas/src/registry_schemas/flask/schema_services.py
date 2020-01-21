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
"""Flask Plugin to manage the use of the Registry JSONSchemas.

Schemas are loaded, globally cached and can be optionally verified on initial load.
Validations are made against these pre-loaded schemas.

Best practice is to validate the schemas using the pytest framework and only deploying once fully compliant.
"""
import json

from flask import g

from registry_schemas import get_schema_store, validate


class SchemaServices():
    """Provides services to use the set of JSONSchemas used by the Registry for legal filings.

    For ease of use, this service is built like a Flask Extension.
    This allows for schemas to be globally loaded and cached reducing future IO contention.
    """

    def __init__(self, app=None):
        """Initializer, supports setting the app context on instantiation."""
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the Flask extension after creation.

        :param app: Flask app
        :return: naked
        """
        self.app = app
        app.teardown_appcontext(self.teardown)

    def teardown(self, exception):  # pylint: disable=unused-argument,no-self-use
        """Clean up whatever the extension has created as part of the Flask teardown lifecycle.

        pylint added so that the Flask method signature matches.
        """
        store = g.pop('rsbc_filing_schema_store', None)

        if store:
            store.clear()
            store = None

    @property
    def rsbc_filing_schema_store(self) -> dict:
        """Return the cached schema_store.

        If this is running in a Flask context,
        then it will return the dict cache holding the JSONSchemas
        used by the Registry for legal filings.
        :return: dict
        """
        if 'rsbc_filing_schema_store' not in g:
            g.rsbc_filing_schema_store = get_schema_store()

        return g.rsbc_filing_schema_store

    def validate(self, json_data: json, schema_id: str):
        """Return the outcome of the util.validate function."""
        return validate(json_data=json_data,
                        schema_id=schema_id,
                        schema_store=self.rsbc_filing_schema_store,
                        validate_schema=False,
                        schema_search_path=None)
