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
"""Utilities to load and validate against JSONSchemas.

Test helper functions to load and assert that a JSON payload validates against a defined schema.
"""
import json
from os import listdir, path
from typing import Tuple

from jsonschema import Draft7Validator, RefResolver, SchemaError, draft7_format_checker


BASE_URI = 'https://bcrs.gov.bc.ca/.well_known/schemas'


def get_schema(filename: str) -> dict:
    """Return the given schema file identified by filename."""
    return _load_json_schema(filename)


def _load_json_schema(filename: str):
    """Return the given schema file identified by filename."""
    relative_path = path.join('schemas', filename)
    absolute_path = path.join(path.dirname(__file__), relative_path)

    with open(absolute_path, 'r') as schema_file:
        schema = json.loads(schema_file.read())

        return schema


def get_schema_store(validate_schema: bool = False, schema_search_path: str = None) -> dict:
    """Return a schema_store as a dict.

    The default returns schema_store of the default schemas found in this package.
    """
    try:
        if not schema_search_path:
            schema_search_path = path.join(path.dirname(__file__), 'schemas')
        schemastore = {}
        fnames = listdir(schema_search_path)
        for fname in fnames:
            fpath = path.join(schema_search_path, fname)
            if fpath[-5:] == '.json':
                with open(fpath, 'r') as schema_fd:
                    schema = json.load(schema_fd)
                    if '$id' in schema:
                        schemastore[schema['$id']] = schema

        if validate_schema:
            for _, schema in schemastore.items():
                Draft7Validator.check_schema(schema)

        return schemastore
    except (SchemaError, json.JSONDecodeError) as error:
        # handle schema error
        raise error


def validate(json_data: json,
             schema_id: str,
             schema_store: dict = None,
             validate_schema: bool = False,
             schema_search_path: str = None
             ) -> Tuple[bool, iter]:
    """Load the json file and validate against loaded schema."""
    try:
        if not schema_search_path:
            schema_search_path = path.join(path.dirname(__file__), 'schemas')

        if not schema_store:
            schema_store = get_schema_store(validate_schema, schema_search_path)

        schema = schema_store.get(f'{BASE_URI}/{schema_id}')
        if validate_schema:
            Draft7Validator.check_schema(schema)

        schema_file_path = path.join(schema_search_path, schema_id)
        resolver = RefResolver(f'file://{schema_file_path}.json', schema, schema_store)

        if Draft7Validator(schema,
                           format_checker=draft7_format_checker,
                           resolver=resolver
                           ) \
                .is_valid(json_data):
            return True, None

        errors = Draft7Validator(schema,
                                 format_checker=draft7_format_checker,
                                 resolver=resolver
                                 ) \
            .iter_errors(json_data)
        return False, errors

    except SchemaError as error:
        # handle schema error
        return False, error
