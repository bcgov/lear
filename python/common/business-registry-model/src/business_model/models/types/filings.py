
from business_model.utils.base import BaseEnum


class FilingTypes(BaseEnum):
    """Enum for Filing Types."""

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
    CHANGEOFOFFICERS = 'changeOfOfficers'
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
    INTENTTOLIQUIDATE = 'intentToLiquidate'
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

class FilingSubTypes(BaseEnum):
    """Enum for Filing Sub Types."""

    pass

class DissolutionTypes(FilingSubTypes):
    """Enum for Dissolution Types."""

    VOLUNTARY = 'voluntary'
    ADMINISTRATIVE = 'administrative'
    INVOLUNTARY = 'involuntary'

class RestorationTypes(FilingSubTypes):
    """Enum for Restoration Types."""

    FULL = 'fullRestoration'
    LIMITED = 'limitedRestoration'
    LIMITED_EXT = 'limitedRestorationExtension'
    LIMITED_TO_FULL = 'limitedRestorationToFull'

class AmalgamationTypes(FilingSubTypes):
    """Enum for Amalgamation Types."""

    REGULAR = 'regular'
    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'

class TransparencyRegisterTypes(FilingSubTypes):
    """Enum for Transparency Register Types."""

    ANNUAL = 'annual'
    CHANGE = 'change'
    INITIAL = 'initial'
