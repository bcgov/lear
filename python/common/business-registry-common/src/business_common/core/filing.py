from enum import Enum
from typing import Final

class Filing:
    class Status(str, Enum):
        """Render an Enum of the Filing Statuses."""

        COMPLETED = 'COMPLETED'
        CORRECTED = 'CORRECTED'
        DRAFT = 'DRAFT'
        EPOCH = 'EPOCH'
        ERROR = 'ERROR'
        PAID = 'PAID'
        PENDING = 'PENDING'
        PAPER_ONLY = 'PAPER_ONLY'
        PENDING_CORRECTION = 'PENDING_CORRECTION'
        WITHDRAWN = 'WITHDRAWN'

        # filings with staff review
        APPROVED = 'APPROVED'
        AWAITING_REVIEW = 'AWAITING_REVIEW'
        CHANGE_REQUESTED = 'CHANGE_REQUESTED'
        REJECTED = 'REJECTED'

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

    class FilingTypesCompact(str, Enum):
        """Render enum for filing types with sub-types."""

        DISSOLUTION_VOLUNTARY = 'dissolution.voluntary'
        DISSOLUTION_ADMINISTRATIVE = 'dissolution.administrative'
        RESTORATION_FULL_RESTORATION = 'restoration.fullRestoration'
        RESTORATION_LIMITED_RESTORATION = 'restoration.limitedRestoration'
        RESTORATION_LIMITED_RESTORATION_EXT = 'restoration.limitedRestorationExtension'
        RESTORATION_LIMITED_RESTORATION_TO_FULL = 'restoration.limitedRestorationToFull'
        AMALGAMATION_APPLICATION_REGULAR = 'amalgamationApplication.regular'
        AMALGAMATION_APPLICATION_VERTICAL = 'amalgamationApplication.vertical'
        AMALGAMATION_APPLICATION_HORIZONTAL = 'amalgamationApplication.horizontal'
        TRANSPARENCY_REGISTER_ANNUAL = 'transparencyRegister.annual'
        TRANSPARENCY_REGISTER_CHANGE = 'transparencyRegister.change'
        TRANSPARENCY_REGISTER_INITIAL = 'transparencyRegister.initial'

    NEW_BUSINESS_FILING_TYPES: Final = [
        FilingTypes.AMALGAMATIONAPPLICATION,
        FilingTypes.CONTINUATIONIN,
        FilingTypes.INCORPORATIONAPPLICATION,
        FilingTypes.REGISTRATION,
    ]
