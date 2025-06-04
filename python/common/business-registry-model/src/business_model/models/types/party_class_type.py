
from business_model.utils.base import BaseEnum


class PartyClassType(BaseEnum):
    """Render an Enum of the party class types."""

    ATTORNEY = 'attorney'
    AGENT = 'agent'
    DIRECTOR = 'director'
    OFFICER = 'officer'
