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
from enum import Enum, auto


class AutoName(str, Enum):
    """Replace autoname from Enum class."""

    # pragma warning disable S5720; # noqa: E265
    # disable sonar cloud complaining about this signature
    def _generate_next_value_(name, start, count, last_values):  # pylint: disable=W0221,E0213 # noqa: N805
        """Return the name of the key, but in lowercase."""
        return name.lower()
    # pragma warning enable S5720; # noqa: E265


class ErrorCode(AutoName):
    """Enum of the system error codes."""

    DOCUMENT_NOT_FOUND = auto()
    FILING_NOT_FOUND = auto()
    FURNISHING_NOT_FOUND = auto()
    MISSING_BUSINESS = auto()
    NOT_AUTHORIZED = auto()
