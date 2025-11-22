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
"""Common validation entry point for all filing submissions."""

from legal_api.errors import Error

from .comment import validate as comment_validate
from .schemas import validate_against_schema


def validate(comment_json: dict, is_filing: bool) -> Error:
    """Validate the annual report JSON."""
    err = validate_against_schema(comment_json)
    if err:
        return err

    err = None
    err = comment_validate(comment_json, is_filing)
    if err:
        return err

    return None
