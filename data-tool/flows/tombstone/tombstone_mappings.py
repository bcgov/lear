from enum import Enum

class EventFilings(str, Enum):
    # IA
    FILE_ICORP = 'FILE_ICORP'
    FILE_ICORU = 'FILE_ICORU'
    FILE_ICORC = 'FILE_ICORC'
    CONVICORP_NULL = 'CONVICORP_NULL'

    # AR
    FILE_ANNBC = 'FILE_ANNBC'

    # CoA
    FILE_APTRA = 'FILE_APTRA'
    FILE_NOERA = 'FILE_NOERA'  # never happened so far
    FILE_NOCAD = 'FILE_NOCAD'

    # CoD
    FILE_NOCDR = 'FILE_NOCDR'

    # # Alteration
    # FILE_NOALA = 'FILE_NOALA'
    # FILE_NOALB = 'FILE_NOALB'
    # FILE_NOALU = 'FILE_NOALU'
    # FILE_NOALC = 'FILE_NOALC'
    # FILE_AM_PF = 'FILE_AM_PF'
    # FILE_AM_PO = 'FILE_AM_PO'
    # FILE_AM_TR = 'FILE_AM_TR'
    # # FILE_AM_AR = 'FILE_AM_AR' # TODO
    # FILE_AM_BC = 'FILE_AM_BC'
    # FILE_AM_DI = 'FILE_AM_DI'
    # FILE_AM_DO = 'FILE_AM_DO'
    # FILE_AM_LI = 'FILE_AM_LI'
    # # FILE_AM_RM = 'FILE_AM_RM' # for liquidation
    # FILE_AM_RR = 'FILE_AM_RR'
    # FILE_AM_SS = 'FILE_AM_SS'

    # transition
    FILE_TRANS = 'FILE_TRANS'


    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
    

EVENT_FILING_LEAR_TARGET_MAPPING = {
    EventFilings.FILE_ICORP: 'incorporationApplication',
    EventFilings.FILE_ICORU: 'incorporationApplication',
    EventFilings.FILE_ICORC: 'incorporationApplication',
    EventFilings.CONVICORP_NULL: 'incorporationApplication',

    EventFilings.FILE_ANNBC: 'annualReport',

    EventFilings.FILE_APTRA: 'changeOfAddress',
    EventFilings.FILE_NOERA: 'changeOfAddress',
    EventFilings.FILE_NOCAD: 'changeOfAddress',

    EventFilings.FILE_NOCDR: 'changeOfDirectors',

    EventFilings.FILE_TRANS: 'transition',

    # subtype example
    # EventFilings.FILE_AMALR: ['amalgamationApplication', 'regular']
}


LEAR_FILING_BUSINESS_UPDATE_MAPPING = {
    'changeOfAddress': 'last_coa_date',
    'changeOfDirectors': 'last_cod_date',
    'agmExtension': 'last_agm_date',
    # TODO: 'dissolution_date' - dissolution, dissolved? Amalgamating business, put back on, restoration
    # TODO: 'restoration_expiry_date' - limited restoration, limited restoration extension, restorationApplication?
}


LEAR_STATE_FILINGS = [
    'dissolution',
    'restoration',
    'putBackOn',
    'continuationOut',
    # TODO: other state filings that lear doesn't support for now e.g. liquidation
    
    # ingore the following since we won't map to them
    # 'dissolved', 'restorationApplication', 'continuedOut'
]

