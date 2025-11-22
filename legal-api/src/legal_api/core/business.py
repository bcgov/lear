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
# limitations under the License
"""The business and its historical values.

This is the core business class.
It is used to represent a business and its historical values.
"""
import re
from enum import Enum, EnumMeta
from typing import Final, Optional

from legal_api.models import Business


class BaseMeta(EnumMeta):
    """Meta class for the enum."""

    def __contains__(cls, other):  # pylint: disable=C0203
        """Return True if 'in' the Enum."""
        try:
            cls(other)  # pylint: disable=no-value-for-parameter
        except ValueError:
            return False
        else:
            return True


class BusinessType(str, Enum, metaclass=BaseMeta):
    """The business type."""

    CONTINUE_IN = "C"
    COOPERATIVE = "CP"
    CORPORATION = "BC"
    INDIVIDUAL = "FP"
    PARTNERSHIP_AND_SOLE_PROP = "FM"
    TRUST = "TRUST"
    OTHER = "OT"
    DEFAULT = "OT" # noqa: PIE796

    @classmethod
    def get_enum_by_value(cls, value: str) -> Optional[str]:
        """Return the enum by value."""
        for enum_value in cls:
            if enum_value.value == value:
                return enum_value
        return None


MAX_IDENTIFIER_NUM_LENGTH: Final[int] = 7


class BusinessIdentifier:
    """The business identifier."""

    @staticmethod
    def validate_format(value: str) -> bool:
        """Validate the business identifier."""
        legal_type = value[:re.search(r"\d", value).start()]

        return not (legal_type not in BusinessType or not value[value.find(legal_type) + len(legal_type):].isdigit())

    @staticmethod
    def next_identifier(business_type: BusinessType) -> Optional[str]:
        """Get the next identifier."""
        if not (business_type in BusinessType and
                (sequence_val := Business.get_next_value_from_sequence(business_type))):
            return None

        return f"{business_type.value}{str(sequence_val).zfill(MAX_IDENTIFIER_NUM_LENGTH)}"
