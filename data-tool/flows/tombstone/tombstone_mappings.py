from enum import Enum


class EventFilings(str, Enum):
    # AGM Extension
    FILE_AGMDT = 'FILE_AGMDT'

    # AGM Location Change
    FILE_AGMLC = 'FILE_AGMLC'

    # TODO: Alteration
    FILE_NOALA = 'FILE_NOALA'
    FILE_NOALB = 'FILE_NOALB'
    FILE_NOALU = 'FILE_NOALU'
    FILE_NOALC = 'FILE_NOALC'
    FILE_AM_PF = 'FILE_AM_PF'
    FILE_AM_PO = 'FILE_AM_PO'
    FILE_AM_TR = 'FILE_AM_TR'
    FILE_AM_AR = 'FILE_AM_AR'
    FILE_AM_BC = 'FILE_AM_BC'
    FILE_AM_DI = 'FILE_AM_DI'
    FILE_AM_DO = 'FILE_AM_DO'
    FILE_AM_LI = 'FILE_AM_LI'
    FILE_AM_RM = 'FILE_AM_RM'
    FILE_AM_RR = 'FILE_AM_RR'
    FILE_AM_SS = 'FILE_AM_SS'

    # TODO: Amalgamation Out Consent - unsupported
    # TODO: Amalgamation Out - unsupported

    # Amalgamation Appliation
    FILE_AMALH = 'FILE_AMALH'
    FILE_AMALR = 'FILE_AMALR'
    FILE_AMALV = 'FILE_AMALV'

    FILE_AMLHU = 'FILE_AMLHU'
    FILE_AMLRU = 'FILE_AMLRU'
    FILE_AMLVU = 'FILE_AMLVU'

    FILE_AMLHC = 'FILE_AMLHC'
    FILE_AMLRC = 'FILE_AMLRC'
    FILE_AMLVC = 'FILE_AMLVC'

    # Annual Report
    FILE_ANNBC = 'FILE_ANNBC'

    # Change of Address
    FILE_APTRA = 'FILE_APTRA'
    FILE_NOERA = 'FILE_NOERA'
    FILE_NOCAD = 'FILE_NOCAD'

    # Change of Directors
    FILE_NOCDR = 'FILE_NOCDR'

    # Consent Continuation Out
    FILE_CONTO = 'FILE_CONTO'
    
    # Continuation Out
    FILE_COUTI = 'FILE_COUTI'
    
    # Continuation In
    FILE_CONTI = 'FILE_CONTI'
    FILE_CONTU = 'FILE_CONTU'
    FILE_CONTC = 'FILE_CONTC'

    # TODO: Correction
    FILE_CO_AR = 'FILE_CO_AR'
    FILE_CO_BC = 'FILE_CO_BC'
    FILE_CO_DI = 'FILE_CO_DI'
    FILE_CO_DO = 'FILE_CO_DO'
    FILE_CO_LI = 'FILE_CO_LI'
    FILE_CO_PF = 'FILE_CO_PF'
    FILE_CO_PO = 'FILE_CO_PO'
    FILE_CO_RM = 'FILE_CO_RM'
    FILE_CO_RR = 'FILE_CO_RR'
    FILE_CO_SS = 'FILE_CO_SS'
    FILE_CO_TR = 'FILE_CO_TR'
    FILE_CORRT = 'FILE_CORRT'

    # Court Order
    FILE_COURT = 'FILE_COURT'

    # Delay of Dissolution - unsupported
    FILE_DISDE = 'FILE_DISDE'

    # Dissolution
    ## voluntary
    FILE_ADVD2 = 'FILE_ADVD2'
    FILE_DISLV = 'FILE_DISLV'
    FILE_ADVDS = 'FILE_ADVDS'
    ## admin
    FILE_DISLC = 'FILE_DISLC'
    FILE_ADCOL = 'FILE_ADCOL'
    # involuntary
    SYSDF_NULL = 'SYSDF_NULL'
    SYSDT_NULL = 'SYSDT_NULL'

    # Incorporation Application
    FILE_ICORP = 'FILE_ICORP'
    FILE_ICORU = 'FILE_ICORU'
    FILE_ICORC = 'FILE_ICORC'
    CONVICORP_NULL = 'CONVICORP_NULL'

    # TODO: Ledger - unsupported
    # TODO: Liquidation - unsupported

    # Notice of Withdrawal
    FILE_NWITH = 'FILE_NWITH'

    # Registrar's Notation
    FILE_REGSN = 'FILE_REGSN'

    # Registrar's Order
    FILE_REGSO = 'FILE_REGSO'

    # Restoration
    FILE_RESTL = 'FILE_RESTL'
    FILE_RESTF = 'FILE_RESTF'
    FILE_RESXL = 'FILE_RESXL'
    FILE_RESXF = 'FILE_RESXF'
    FILE_RUSTF = 'FILE_RUSTF'
    FILE_RUSTL = 'FILE_RUSTL'
    FILE_RUSXL = 'FILE_RUSXL'
    FILE_RUSXF = 'FILE_RUSXF'


    # Transition
    FILE_TRANS = 'FILE_TRANS'
    FILE_TRANP = 'FILE_TRANP'

    # TODO:
    # Other COLIN events: CONV*, Adim Corp (ADCORP, BNUPD, ADMIN), XPRO filing


    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
    

EVENT_FILING_LEAR_TARGET_MAPPING = {
    EventFilings.FILE_AGMDT: 'agmExtension',
    EventFilings.FILE_AGMLC: 'agmLocationChange',

    # TODO: Alteration
    # TODO: Amalgamation Out Consent - unsupported
    # TODO: Amalgamation Out - unsupported

    EventFilings.FILE_AMALH: ['amalgamationApplication', 'horizontal'],
    EventFilings.FILE_AMALR: ['amalgamationApplication', 'regular'],
    EventFilings.FILE_AMALV: ['amalgamationApplication', 'vertical'],
    EventFilings.FILE_AMLHU: ['amalgamationApplication', 'horizontal'],
    EventFilings.FILE_AMLRU: ['amalgamationApplication', 'regular'],
    EventFilings.FILE_AMLVU: ['amalgamationApplication', 'vertical'],
    EventFilings.FILE_AMLHC: ['amalgamationApplication', 'horizontal'],
    EventFilings.FILE_AMLRC: ['amalgamationApplication', 'regular'],
    EventFilings.FILE_AMLVC: ['amalgamationApplication', 'vertical'],

    EventFilings.FILE_ANNBC: 'annualReport',

    EventFilings.FILE_APTRA: 'changeOfAddress',
    EventFilings.FILE_NOERA: 'changeOfAddress',
    EventFilings.FILE_NOCAD: 'changeOfAddress',

    EventFilings.FILE_NOCDR: 'changeOfDirectors',

    EventFilings.FILE_CONTO: 'consentContinuationOut',
    EventFilings.FILE_COUTI: 'continuationOut',

    EventFilings.FILE_CONTI: 'continuationIn',
    EventFilings.FILE_CONTU: 'continuationIn',
    EventFilings.FILE_CONTC: 'continuationIn',

    # TODO: Correction

    EventFilings.FILE_COURT: 'courtOrder',

    EventFilings.FILE_DISDE: 'delayOfDissolution',  # unsupported

    EventFilings.FILE_ADVD2: ['dissolution', 'voluntary'],
    EventFilings.FILE_DISLV: ['dissolution', 'voluntary'],
    EventFilings.FILE_ADVDS: ['dissolution', 'voluntary'],
    EventFilings.FILE_ADVDS: ['dissolution', 'administrative'],
    EventFilings.FILE_ADVDS: ['dissolution', 'administrative'],
    EventFilings.SYSDF_NULL: ['dissolution', 'involuntary'],
    EventFilings.SYSDT_NULL: ['dissolution', 'involuntary'],

    EventFilings.FILE_ICORP: 'incorporationApplication',
    EventFilings.FILE_ICORU: 'incorporationApplication',
    EventFilings.FILE_ICORC: 'incorporationApplication',
    EventFilings.CONVICORP_NULL: 'incorporationApplication',

    # TODO: Ledger - unsupported
    # TODO: Liquidation - unsupported

    EventFilings.FILE_NWITH: 'noticeOfWithdrawal',

    EventFilings.FILE_REGSN: 'registrarsNotation',
    EventFilings.FILE_REGSO: 'registrarsOrder',

    EventFilings.FILE_RESTL: ['restoration', 'limitedRestoration'],
    EventFilings.FILE_RESTF: ['restoration', 'fullRestoration'],
    EventFilings.FILE_RESXL: ['restoration', 'limitedRestorationExtension'],
    EventFilings.FILE_RESXF: ['restoration', 'limitedRestorationToFull'],
    EventFilings.FILE_RUSTF: ['restoration', 'fullRestoration'],
    EventFilings.FILE_RUSTL: ['restoration', 'limitedRestoration'],
    EventFilings.FILE_RUSXL: ['restoration', 'limitedRestorationExtension'],
    EventFilings.FILE_RUSXF: ['restoration', 'limitedRestorationToFull'],

    EventFilings.FILE_TRANS: 'transition',
    EventFilings.FILE_TRANP: 'transition',
}


LEAR_FILING_BUSINESS_UPDATE_MAPPING = {
    'incorporationApplication': ['last_coa_date', 'last_cod_date'],
    'changeOfAddress': ['last_coa_date'],
    'changeOfDirectors': ['last_cod_date'],
    'agmExtension': ['last_agm_date'],
    # TODO: 'dissolution_date' - Amalgamating business, continuation out
    'dissolution': ['dissolution_date'],
    'putBackOn': ['dissolution_date'],
    'restoration': ['dissolution_date'],
    # TODO: 'restoration_expiry_date' - limited restoration, limited restoration extension
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

