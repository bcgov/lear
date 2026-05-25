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
"""Application Specific Exceptions, to manage the business errors.

@log_error - a decorator to automatically log the exception to the logger provided

BusinessException - error, status_code - Business rules error
error - a description of the error {code / description: classname / full text}
status_code - where possible use HTTP Error Codes
"""


class BusinessException(Exception):  # noqa: N818
    """Exception that adds error code and error name, that can be used for i18n support."""

    def __init__(self, error, status_code, *args, **kwargs):
        """Return a valid BusinessException."""
        super().__init__(*args, **kwargs)
        self.error = error
        self.status_code = status_code
