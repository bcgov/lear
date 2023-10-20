"""Enum Utilities."""
from enum import auto  # noqa: F401
from enum import Enum
from enum import EnumMeta
from typing import Optional


class BaseMeta(EnumMeta):
    """Meta class for the enum."""

    def __contains__(self, other):
        """Return True if 'in' the Enum."""
        try:
            self(other)
        except ValueError:
            return False
        else:
            return True


class BaseEnum(str, Enum, metaclass=BaseMeta):
    """Replace autoname from Enum class."""

    @classmethod
    def get_enum_by_value(cls, value: str) -> Optional[str]:
        """Return the enum by value."""
        for enum_value in cls:
            if enum_value.value == value:
                return enum_value
        return None

    @classmethod
    def get_enum_by_name(cls, value: str) -> Optional[str]:
        """Return the enum by value."""
        for enum_value in cls:
            if enum_value.name == value:
                return enum_value
        return None

    def _generate_next_value_(name, start, count, last_values):
        """Return the name of the key."""
        return name
