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

from typing import Union

from flask import current_app

from legal_api.models import Party, User

DBC_ENABLED_BUSINESS_TYPES_FLAG = "dbc-enabled-business-types"


def determine_allowed_business_types(valid_registration_types: list[str],
                                     valid_incorporation_types: list[str]) -> list[str]:
    """Determine if the business type is allowed for digital credentials based on flags."""
    # Import inside function to avoid circular dependency and ensure app context is available
    from legal_api.services import flags

    if not flags.is_on(DBC_ENABLED_BUSINESS_TYPES_FLAG):
        current_app.logger.warning("%s is OFF", DBC_ENABLED_BUSINESS_TYPES_FLAG)
        return []

    flag_obj = flags.value(DBC_ENABLED_BUSINESS_TYPES_FLAG)

    # Validate dbc-enabled-business-types is the right format to parse out
    if not isinstance(flag_obj, dict) or "types" not in flag_obj or not isinstance(flag_obj["types"], list):
        current_app.logger.error("Invalid %s flag value: %s", DBC_ENABLED_BUSINESS_TYPES_FLAG, flag_obj)
        return []

    supported_types = valid_registration_types + valid_incorporation_types
    valid_business_types = list(set(flag_obj["types"]) & set(supported_types))
    return valid_business_types


class FormattedUser:
    """Formatted user class."""

    first_name: str
    last_name: str

    def __init__(self, user: Union[User, Party]):
        """Initialize the formatted user."""
        first_name, last_name = self._formatted_user(user)
        self.first_name = first_name
        self.last_name = last_name

    def _formatted_user(self, user: Union[User, Party]) -> dict:
        """Return the formatted name of the user."""
        first_name = (getattr(user, "firstname", "") or getattr(
            user, "first_name", "") or "").lower()
        last_name = (getattr(user, "lastname", "") or getattr(
            user, "last_name", "") or "").lower()
        middle_name = (getattr(user, "middlename", "") or getattr(
            user, "middle_initial", "") or "").lower()

        if middle_name:
            first_name = f"{first_name} {middle_name}"

        return first_name, last_name
