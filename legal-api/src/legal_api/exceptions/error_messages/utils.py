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
"""Application Common Error Messages."""
from string import Formatter
from typing import Optional

from flask_babel import _ as babel  # noqa: N813,I005

from .codes import ErrorCode
from .messages import ERROR_MESSAGES


class MissingKeysFormatter(Formatter):
    """Format the string, using the key names if the values are missing."""

    def get_value(self, key, args, kwargs):
        """Return the ley name if the value is missing."""
        if isinstance(key, str):
            try:
                return kwargs[key]
            except KeyError:
                return key
        else:
            return Formatter.get_value(key, args, kwargs)  # pylint: disable=E1120


def get_error_message(error_code: ErrorCode, **kwargs) -> Optional[str]:
    """Get a localized, formatted error message using the templates in the ERROR_MESSAGES dict."""
    if template := ERROR_MESSAGES.get(error_code, None):
        fmt = MissingKeysFormatter()
        template = babel(template)
        msg = fmt.format(template, **kwargs)
        return msg

    return None
