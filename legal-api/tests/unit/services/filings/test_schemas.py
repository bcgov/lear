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
"""Test suite to ensure the json data is validated correctly against the published JSONSchemas."""
import copy
from http import HTTPStatus

from registry_schemas.example_data import ANNUAL_REPORT

from legal_api.services.filings.validations import schemas


def test_validate_schema_good_ar(app):
    """Assert that a valid filing passes validation."""
    # validate_schema(json_data: Dict = None) -> Tuple(int, str):
    with app.app_context():
        err = schemas.validate_against_schema(ANNUAL_REPORT)

    assert not err


def test_validate_schema_bad_ar(app):
    """Assert that an invalid AR returns an error."""
    # validate_schema(json_data: Dict = None) -> Tuple(int, str):
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar['filing']['header'].pop('name')

    with app.app_context():
        err = schemas.validate_against_schema(ar)

    assert err.msg == [{'error': "'name' is a required property", 'path': 'filing/header'}]
    assert err.code == HTTPStatus.UNPROCESSABLE_ENTITY
