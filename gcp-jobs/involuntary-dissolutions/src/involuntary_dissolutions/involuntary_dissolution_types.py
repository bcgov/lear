from enum import Enum


class DissolutionTypes(str, Enum):
    """Dissolution types."""

    ADMINISTRATIVE = "administrative"
    COURT_ORDERED_LIQUIDATION = "courtOrderedLiquidation"
    INVOLUNTARY = "involuntary"
    VOLUNTARY = "voluntary"
    VOLUNTARY_LIQUIDATION = "voluntaryLiquidation"
