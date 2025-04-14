from enum import Enum


class FilingTypes(str, Enum):
    """Render an Enum of all Filing Types."""

    ADMIN_FREEZE = 'adminFreeze'
    AGMEXTENSION = 'agmExtension'
    AGMLOCATIONCHANGE = 'agmLocationChange'
    ALTERATION = 'alteration'
    AMALGAMATIONAPPLICATION = 'amalgamationApplication'
    AMALGAMATIONOUT = 'amalgamationOut'
    AMENDEDAGM = 'amendedAGM'
    AMENDEDANNUALREPORT = 'amendedAnnualReport'
    AMENDEDCHANGEOFDIRECTORS = 'amendedChangeOfDirectors'
    ANNUALREPORT = 'annualReport'
    APPOINTRECEIVER = 'appointReceiver'
    CEASERECEIVER = 'ceaseReceiver'
    CHANGEOFADDRESS = 'changeOfAddress'
    CHANGEOFDIRECTORS = 'changeOfDirectors'
    CHANGEOFNAME = 'changeOfName'
    CHANGEOFREGISTRATION = 'changeOfRegistration'
    CONSENTAMALGAMATIONOUT = 'consentAmalgamationOut'
    CONSENTCONTINUATIONOUT = 'consentContinuationOut'
    CONTINUATIONIN = 'continuationIn'
    CONTINUATIONOUT = 'continuationOut'
    CONTINUEDOUT = 'continuedOut'
    CONVERSION = 'conversion'
    CORRECTION = 'correction'
    COURTORDER = 'courtOrder'
    DISSOLUTION = 'dissolution'
    DISSOLVED = 'dissolved'
    INCORPORATIONAPPLICATION = 'incorporationApplication'
    NOTICEOFWITHDRAWAL = 'noticeOfWithdrawal'
    PUTBACKOFF = 'putBackOff'
    PUTBACKON = 'putBackOn'
    REGISTRARSNOTATION = 'registrarsNotation'
    REGISTRARSORDER = 'registrarsOrder'
    REGISTRATION = 'registration'
    RESTORATION = 'restoration'
    RESTORATIONAPPLICATION = 'restorationApplication'
    SPECIALRESOLUTION = 'specialResolution'
    TRANSITION = 'transition'
    TRANSPARENCY_REGISTER = 'transparencyRegister'

class DissolutionTypes(str, Enum):
    """Dissolution types."""

    ADMINISTRATIVE = 'administrative'
    COURT_ORDERED_LIQUIDATION = 'courtOrderedLiquidation'
    INVOLUNTARY = 'involuntary'
    VOLUNTARY = 'voluntary'
    VOLUNTARY_LIQUIDATION = 'voluntaryLiquidation'