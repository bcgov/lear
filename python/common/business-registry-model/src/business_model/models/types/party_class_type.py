
from business_model.utils.base import BaseEnum
from enum import auto


class PartyClassType(BaseEnum):
    """Render an Enum of the party class types."""

    ATTORNEY = auto()
    AGENT = auto()
    DIRECTOR = auto()
    OFFICER = auto()
