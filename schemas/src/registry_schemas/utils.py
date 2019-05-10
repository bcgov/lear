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

from jsonschema import Draft7Validator, draft7_format_checker, RefResolver, SchemaError, ValidationError

BASE_URI = 'https://bcrs.gov.bc.ca'


def validate_schema(data: dict, schema_file: dict) -> Tuple[bool, iter]:
    """Do assertion that data validates against the JSONSchema in schema_file."""
    schema = _load_json_schema(schema_file)

    if Draft7Validator(schema, format_checker=draft7_format_checker).is_valid(data):
        return True, None

    errors = Draft7Validator(schema,
                             format_checker=draft7_format_checker
                             ).iter_errors(data)
    return False, errors


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


def validate(json_data, schema_id, schema_search_path=path.join(path.dirname(__file__), 'schemas')):
    """
    load the json file and validate against loaded schema
    """
    try:
        schemastore = {}
        schema = None
        fnames = listdir(schema_search_path)
        for fname in fnames:
            fpath = path.join(schema_search_path, fname)
            if fpath[-5:] == ".json":
                with open(fpath, "r") as schema_fd:
                    schema = json.load(schema_fd)
                    if "$id" in schema:
                        schemastore[schema["$id"]] = schema

        schema = schemastore.get(f'{BASE_URI}/{schema_id}')
        Draft7Validator.check_schema(schema)
        resolver = RefResolver("file://%s.json" % path.join(schema_search_path, schema_id), schema, schemastore)
        Draft7Validator(schema, resolver=resolver).validate(json_data)
        return True
    except ValidationError as error:
        # handle validation error
        pass
    except SchemaError as error:
        # handle schema error
        pass
    return False
