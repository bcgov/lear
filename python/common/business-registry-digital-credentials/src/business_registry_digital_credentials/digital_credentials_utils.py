# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This provides utility functions for specific actions related to digital credentials."""

from business_model.models import Party, User


def determine_allowed_business_types(
    enabled_business_types: list[str] | None,
    valid_registration_types: list[str],
    valid_incorporation_types: list[str],
) -> list[str]:
    """Return the intersection of caller-provided enabled types and DBC-supported types.

    ``enabled_business_types`` is the feature-flag-resolved list of business types the
    operator wants enabled for DBC. The caller (e.g. legal-api) is responsible for
    loading the LaunchDarkly flag and passing the resolved value. ``None`` or ``[]``
    means "DBC disabled" — returns ``[]``.
    """
    if not enabled_business_types:
        return []

    supported_types = valid_registration_types + valid_incorporation_types
    return list(set(enabled_business_types) & set(supported_types))


class FormattedUser:
    """Formatted user class."""

    first_name: str
    last_name: str

    def __init__(self, user: User | Party):
        """Initialize the formatted user."""
        first_name, last_name = self._formatted_user(user)
        self.first_name = first_name
        self.last_name = last_name

    def _formatted_user(self, user: User | Party) -> tuple[str, str]:
        """Return the formatted name of the user."""
        first_name = (getattr(user, "firstname", "") or getattr(user, "first_name", "") or "").lower()
        last_name = (getattr(user, "lastname", "") or getattr(user, "last_name", "") or "").lower()
        middle_name = (getattr(user, "middlename", "") or getattr(user, "middle_initial", "") or "").lower()

        if middle_name:
            first_name = f"{first_name} {middle_name}"

        return first_name, last_name
