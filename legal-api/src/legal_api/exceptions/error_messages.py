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
"""Application Common Error Messages.
"""
from enum import auto, Enum
from string import Formatter
from typing import Optional

from flask_babel import _ as babel  # noqa: N813, I001, I003 casting _ to babel

class AutoName(str, Enum):
    def _generate_next_value_(name, start, count, last_values):  # pylint: disable=W0221,E0213
        return name.lower()

class ErrorCode(AutoName):
    FILING_NOT_FOUND = auto()
    MISSING_BUSINESS = auto()
    NOT_AUTHORIZED = auto()

ERROR_MESSAGES: dict = {
   ErrorCode.MISSING_BUSINESS: 'Business not found for identifier: {identifier}',
   ErrorCode.FILING_NOT_FOUND: 'Filing: {filing_id} not found for: {identifier}',
   ErrorCode.NOT_AUTHORIZED: 'Not authorized to access business: {identifier}',
}

class MissingKeysFormatter(Formatter):
    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            try:
                return kwargs[key]
            except KeyError:
                return key
        else:
            return Formatter.get_value(key, args, kwargs)  # pylint: disable=E1120


def get_error_message(error_code: ErrorCode, **kwargs) -> Optional[str]:
    if template := ERROR_MESSAGES.get(error_code, None):
        fmt = MissingKeysFormatter()
        template = babel(template)
        msg = fmt.format(template, **kwargs)
        return msg

    return None
