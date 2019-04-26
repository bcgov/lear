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
from os.path import dirname, join
from typing import Tuple

from jsonschema import Draft7Validator, draft7_format_checker


def validate_schema(data: dict, schema_file: dict) -> Tuple[bool, iter]:
    """Do assertion that data validates against the JSONSchema in schema_file."""
    schema = _load_json_schema(schema_file)

    if Draft7Validator(schema, format_checker=draft7_format_checker).is_valid(data):
        return True, None

    errors = Draft7Validator(schema,
                             format_checker=draft7_format_checker
                             ).iter_errors(data)
    return False, errors


def _load_json_schema(filename: str):
    """Return the given schema file identified by filename."""
    # relative_path = join('schemas', filename)
    # absolute_path = join(dirname(__file__), relative_path)
    absolute_path = join(dirname(__file__), filename)

    with open(absolute_path) as schema_file:
        return json.loads(schema_file.read())
