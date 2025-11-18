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
# limitations under the License
"""Filings are legal documents that alter the state of a business."""

from http import HTTPStatus
from typing import Dict

from legal_api.errors import Error
from legal_api.schemas import rsbc_schemas


def validate_against_schema(json_data: Dict = None) -> Error:
    """Validate against the filing schema.

    Returns:
        int: status code of the validation operation using HTTPStatus
        List[Dict]: a list of errors defined as {error:message, path:schemaPath}

    """
    valid, err = rsbc_schemas.validate(json_data, "comment")

    if valid:
        return None

    errors = []
    for error in err:
        errors.append({"path": "/".join(error.path), "error": error.message})
    return Error(HTTPStatus.UNPROCESSABLE_ENTITY, errors)
