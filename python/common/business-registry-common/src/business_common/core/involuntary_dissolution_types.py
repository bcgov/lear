from enum import Enum

class DissolutionTypes(str, Enum):
    """Dissolution types."""

    ADMINISTRATIVE = 'administrative'
    COURT_ORDERED_LIQUIDATION = 'courtOrderedLiquidation'
    INVOLUNTARY = 'involuntary'
    VOLUNTARY = 'voluntary'
    VOLUNTARY_LIQUIDATION = 'voluntaryLiquidation'


class DissolutionStatementTypes(str, Enum):
    """Dissolution statement types."""

    NO_ASSETS_NO_LIABILITIES_197 = '197NoAssetsNoLiabilities'
    NO_ASSETS_PROVISIONS_LIABILITIES_197 = '197NoAssetsProvisionsLiabilities'

    @classmethod
    def has_value(cls, value):
        """Check if enum contains specific value provided via input param."""
        return value in cls._value2member_map_  # pylint: disable=no-member