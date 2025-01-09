from enum import Enum


class EventFilings(str, Enum):
    # AGM Extension
    FILE_AGMDT = 'FILE_AGMDT'

    # AGM Location Change
    FILE_AGMLC = 'FILE_AGMLC'

    # Alteration
    FILE_NOALA = 'FILE_NOALA'
    FILE_NOALB = 'FILE_NOALB'
    FILE_NOALU = 'FILE_NOALU'
    FILE_NOALC = 'FILE_NOALC'
    FILE_AM_BC = 'FILE_AM_BC'
    FILE_AM_LI = 'FILE_AM_LI'
    FILE_AM_RM = 'FILE_AM_RM'
    FILE_AM_SS = 'FILE_AM_SS'

    # TODO: FILE_AM_AR = 'FILE_AM_AR'
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
    FILE_AM_DO = 'FILE_AM_DO'
    FILE_AM_RR = 'FILE_AM_RR'

    # Change of Directors
    FILE_NOCDR = 'FILE_NOCDR'
    FILE_AM_DI = 'FILE_AM_DI'

    # Consent Continuation Out
    FILE_CONTO = 'FILE_CONTO'
    
    # Continuation Out
    FILE_COUTI = 'FILE_COUTI'
    
    # Continuation In
    FILE_CONTI = 'FILE_CONTI'
    FILE_CONTU = 'FILE_CONTU'
    FILE_CONTC = 'FILE_CONTC'

    # Correction
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

    # TODO: Delay of Dissolution - unsupported (need confirmation)
    DISD1_DISDE = 'DISD1_DISDE'
    DISD2_DISDE = 'DISD2_DISDE'

    # Dissolution
    ## voluntary
    FILE_ADVD2 = 'FILE_ADVD2'
    FILE_ADVDS = 'FILE_ADVDS'
    DISLV_NULL = 'DISLV_NULL'
    ## admin
    DISLC_NULL = 'DISLC_NULL'
    SYSDA_NULL = 'SYSDA_NULL'
    SYSDS_NULL = 'SYSDS_NULL'
    # involuntary
    SYSDF_NULL = 'SYSDF_NULL'
    SYSDT_NULL = 'SYSDT_NULL'

    # Incorporation Application
    FILE_ICORP = 'FILE_ICORP'
    FILE_ICORU = 'FILE_ICORU'
    FILE_ICORC = 'FILE_ICORC'
    CONVICORP_NULL = 'CONVICORP_NULL'  # TODO: may need to be removed

    # TODO: Ledger - unsupported

    # TODO: Legacy Other - unsupported
    FILE_AM_PF = 'FILE_AM_PF'
    FILE_AM_PO = 'FILE_AM_PO'
    FILE_AM_TR = 'FILE_AM_TR'

    # TODO: Liquidation - unsupported
    # FILE_ADCOL = 'FILE_ADCOL'

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
    FILE_RUSTL = 'FILE_RUSTL'
    FILE_RUSTF = 'FILE_RUSTF'
    FILE_RUSXL = 'FILE_RUSXL'
    FILE_RUSXF = 'FILE_RUSXF'

    # Transition
    FILE_TRANS = 'FILE_TRANS'
    FILE_TRANP = 'FILE_TRANP'

    # TODO:
    # Other COLIN events:
    # CONV*, Adim Corp (ADCORP, BNUPD, ADMIN), XPRO filing
    # SYSDL, SYST
    # more legacyOther filings


    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_
    

EVENT_FILING_LEAR_TARGET_MAPPING = {
    EventFilings.FILE_AGMDT: 'agmExtension',
    EventFilings.FILE_AGMLC: 'agmLocationChange',

    EventFilings.FILE_NOALA: 'alteration',
    EventFilings.FILE_NOALB: 'alteration',
    EventFilings.FILE_NOALU: 'alteration',
    EventFilings.FILE_NOALC: 'alteration',
    EventFilings.FILE_AM_BC: 'alteration',
    EventFilings.FILE_AM_LI: 'alteration',
    EventFilings.FILE_AM_RM: 'alteration',
    EventFilings.FILE_AM_SS: 'alteration',

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
    EventFilings.FILE_AM_DO: 'changeOfAddress',
    EventFilings.FILE_AM_RR: 'changeOfAddress',

    EventFilings.FILE_NOCDR: 'changeOfDirectors',
    EventFilings.FILE_AM_DI: 'changeOfDirectors',

    EventFilings.FILE_CONTO: 'consentContinuationOut',
    EventFilings.FILE_COUTI: 'continuationOut',

    EventFilings.FILE_CONTI: 'continuationIn',
    EventFilings.FILE_CONTU: 'continuationIn',
    EventFilings.FILE_CONTC: 'continuationIn',

    EventFilings.FILE_CO_AR: 'correction',
    EventFilings.FILE_CO_BC: 'correction',
    EventFilings.FILE_CO_DI: 'correction',
    EventFilings.FILE_CO_DO: 'correction',
    EventFilings.FILE_CO_LI: 'correction',
    EventFilings.FILE_CO_PF: 'correction',
    EventFilings.FILE_CO_PO: 'correction',
    EventFilings.FILE_CO_RM: 'correction',
    EventFilings.FILE_CO_RR: 'correction',
    EventFilings.FILE_CO_SS: 'correction',
    EventFilings.FILE_CO_TR: 'correction',
    EventFilings.FILE_CORRT: 'correction',

    EventFilings.FILE_COURT: 'courtOrder',

    # TODO: Delay of Dissolution - unsupported (need confirmation)
    EventFilings.DISD1_DISDE: 'delayOfDissolution',
    EventFilings.DISD2_DISDE: 'delayOfDissolution',

    EventFilings.FILE_ADVD2: ['dissolution', 'voluntary'],
    EventFilings.FILE_ADVDS: ['dissolution', 'voluntary'],
    EventFilings.DISLV_NULL: ['dissolution', 'voluntary'],  # TODO: re-map
    EventFilings.DISLC_NULL: ['dissolution', 'administrative'],  # TODO: re-map
    EventFilings.SYSDA_NULL: ['dissolution', 'administrative'],
    EventFilings.SYSDS_NULL: ['dissolution', 'administrative'],
    EventFilings.SYSDF_NULL: ['dissolution', 'involuntary'],
    EventFilings.SYSDT_NULL: ['dissolution', 'involuntary'],

    EventFilings.FILE_ICORP: 'incorporationApplication',
    EventFilings.FILE_ICORU: 'incorporationApplication',
    EventFilings.FILE_ICORC: 'incorporationApplication',
    EventFilings.CONVICORP_NULL: 'incorporationApplication',  # TODO: re-map

    # TODO: Ledger - unsupported
    # TODO: Legacy Other - unsupported
    EventFilings.FILE_AM_PF: 'legacyOther',
    EventFilings.FILE_AM_PO: 'legacyOther',
    EventFilings.FILE_AM_TR: 'legacyOther',

    # TODO: Liquidation - unsupported

    EventFilings.FILE_NWITH: 'noticeOfWithdrawal',

    EventFilings.FILE_REGSN: 'registrarsNotation',
    EventFilings.FILE_REGSO: 'registrarsOrder',

    EventFilings.FILE_RESTL: ['restoration', 'limitedRestoration'],
    EventFilings.FILE_RESTF: ['restoration', 'fullRestoration'],
    EventFilings.FILE_RESXL: ['restoration', 'limitedRestorationExtension'],
    EventFilings.FILE_RESXF: ['restoration', 'limitedRestorationToFull'],
    EventFilings.FILE_RUSTL: ['restoration', 'limitedRestoration'],
    EventFilings.FILE_RUSTF: ['restoration', 'fullRestoration'],
    EventFilings.FILE_RUSXL: ['restoration', 'limitedRestorationExtension'],
    EventFilings.FILE_RUSXF: ['restoration', 'limitedRestorationToFull'],

    EventFilings.FILE_TRANS: 'transition',
    EventFilings.FILE_TRANP: 'transition',
}


EVENT_FILING_DISPLAY_NAME_MAPPING = {
    EventFilings.FILE_AGMDT: 'Notice of Change - AGM Date',
    EventFilings.FILE_AGMLC: 'Notice of Change - AGM Location',

    EventFilings.FILE_NOALA: 'Notice of Alteration',
    EventFilings.FILE_NOALB: 'Notice of Alteration from a BC Unlimited Liability Company to Become a BC Company',
    EventFilings.FILE_NOALU: 'Notice of Alteration from a BC Company to Become a BC Unlimited Liability Company',
    EventFilings.FILE_NOALC: 'Notice of Alteration from a BC Company to Become a Community Contribution Company',
    EventFilings.FILE_AM_BC: 'Amendment - Translated Name',
    EventFilings.FILE_AM_LI: 'Amendment - Ledger Information',
    EventFilings.FILE_AM_RM: 'Amendment - Receiver or Receiver Manager',
    EventFilings.FILE_AM_SS: 'Amendment - Share Structure',

    # TODO: Amalgamation Out Consent - unsupported
    # TODO: Amalgamation Out - unsupported

    EventFilings.FILE_AMALH: 'Amalgamation Application Short Form (Horizontal)',
    EventFilings.FILE_AMALR: 'Amalgamation Application (Regular)',
    EventFilings.FILE_AMALV: 'Amalgamation Application Short Form (Vertical)',
    EventFilings.FILE_AMLHU: 'Amalgamation Application Short Form (Horizontal) for a BC Unlimited Liability Company',
    EventFilings.FILE_AMLRU: 'Amalgamation Application (Regular) for a BC Unlimited Liability Company',
    EventFilings.FILE_AMLVU: 'Amalgamation Application Short Form (Vertical) for a BC Unlimited Liability Company',
    EventFilings.FILE_AMLHC: 'Amalgamation Application Short Form (Horizontal) for a Community Contribution Company',
    EventFilings.FILE_AMLRC: 'Amalgamation Application (Regular) for a Community Contribution Company',
    EventFilings.FILE_AMLVC: 'Amalgamation Application Short Form (Vertical) for a Community Contribution Company',

    EventFilings.FILE_ANNBC: 'BC Annual Report',  # has suffix of date, dynamically add it during formatting

    EventFilings.FILE_APTRA: 'Application to Transfer Registered Office',
    EventFilings.FILE_NOERA: 'Notice of Elimination of Registered Office',
    EventFilings.FILE_NOCAD: 'Notice of Change of Address',
    EventFilings.FILE_AM_DO: 'Amendment - Dissolved Office',
    EventFilings.FILE_AM_RR: 'Amendment - Registered and Records Offices',

    EventFilings.FILE_NOCDR: 'Notice of Change of Directors', # TODO: some has suffix  - Address Change or Name Correction Only
    EventFilings.FILE_AM_DI: 'Amendment - Director',

    EventFilings.FILE_CONTO: '6 Months Consent to Continue Out',
    EventFilings.FILE_COUTI: 'Instrument of Continuation Out',

    EventFilings.FILE_CONTI: 'Continuation Application',
    EventFilings.FILE_CONTU: 'Continuation Application for a BC Unlimited Liability Company',
    EventFilings.FILE_CONTC: 'Continuation Application for a Community Contribution Company',

    EventFilings.FILE_CO_AR: 'Correction - Annual Report',
    EventFilings.FILE_CO_BC: 'Correction - BC Company Name/Translated Name',
    EventFilings.FILE_CO_DI: 'Correction - Director',
    EventFilings.FILE_CO_DO: 'Correction - Dissolved Office',
    EventFilings.FILE_CO_LI: 'Correction - Ledger Information',
    EventFilings.FILE_CO_PF: 'Correction - Put Back Off',
    EventFilings.FILE_CO_PO: 'Correction - Put Back On',
    EventFilings.FILE_CO_RM: 'Correction - Receiver or Receiver Manager',
    EventFilings.FILE_CO_RR: 'Correction - Registered and Records Offices',
    EventFilings.FILE_CO_SS: 'Correction - Share Structure',
    EventFilings.FILE_CO_TR: 'Correction - Transition',
    EventFilings.FILE_CORRT: 'Correction',

    EventFilings.FILE_COURT: 'Court Order',

    # TODO: Delay of Dissolution - unsupported (need confirmation)
    EventFilings.DISD1_DISDE: "Registrar''s Notation - Dissolution or Cancellation Delay",  # has prefix "Registrar's Notation - "
    EventFilings.DISD2_DISDE: "Registrar''s Notation - Dissolution or Cancellation Delay",

    EventFilings.FILE_ADVD2: 'Application for Dissolution (Voluntary Dissolution)',
    EventFilings.FILE_ADVDS: 'Application for Dissolution (Voluntary Dissolution)',
    EventFilings.DISLV_NULL: None,  # TODO: re-map, voluntary - no ledger in colin + status liquidated
    EventFilings.DISLC_NULL: None,  # TODO: re-map, admin - no ledger in colin + status liquidated
    EventFilings.SYSDA_NULL: None,  # admin - status Administrative Dissolution
    EventFilings.SYSDS_NULL: None,  # admin - status Administrative Dissolution
    EventFilings.SYSDF_NULL: None,  # invol - no ledger in lear & colin
    EventFilings.SYSDT_NULL: None,  # invol - no ledger in lear & colin

    EventFilings.FILE_ICORP: 'Incorporation Application',
    EventFilings.FILE_ICORU: 'Incorporation Application for a BC Unlimited Liability Company',
    EventFilings.FILE_ICORC: 'Incorporation Application for a Community Contribution Company',
    EventFilings.CONVICORP_NULL: None,  # TODO: re-map

    # TODO: Ledger - unsupported
    # TODO: Legacy Other - unsupported
    EventFilings.FILE_AM_PF: 'Amendment - Put Back Off',
    EventFilings.FILE_AM_PO: 'Amendment - Put Back On',
    EventFilings.FILE_AM_TR: 'Amendment - Transition',

    # TODO: Liquidation - unsupported

    EventFilings.FILE_NWITH: 'Notice of Withdrawal',

    EventFilings.FILE_REGSN: "Registrar''s Notation",
    EventFilings.FILE_REGSO: "Registrar''s Order",

    EventFilings.FILE_RESTL: 'Restoration Application - Limited',
    EventFilings.FILE_RESTF: 'Restoration Application - Full',
    EventFilings.FILE_RESXL: 'Restoration Application (Extend Time Limit)',
    EventFilings.FILE_RESXF: 'Restoration Application (Convert Limited to Full)',
    EventFilings.FILE_RUSTL: 'Restoration Application - Limited for a BC Unlimited Liability Company',
    EventFilings.FILE_RUSTF: 'Restoration Application - Full for a BC Unlimited Liability Company',
    EventFilings.FILE_RUSXL: 'Restoration Application (Extend Time Limit) for a BC Unlimited Liability Company',
    EventFilings.FILE_RUSXF: 'Restoration Application (Convert Limited to Full) for a BC Unlimited Liability Company',

    EventFilings.FILE_TRANS: 'Transition Application',
    EventFilings.FILE_TRANP: 'Post Restoration Transition Application',
}


LEAR_FILING_BUSINESS_UPDATE_MAPPING = {
    'incorporationApplication': ['last_coa_date', 'last_cod_date'],
    'changeOfAddress': ['last_coa_date'],
    'changeOfDirectors': ['last_cod_date'],
    'agmExtension': ['last_agm_date'],
    # TODO: 'dissolution_date' - Amalgamating business, continuation out
    # TODO: 'continuation_out_date' - continuation out
    'dissolution': ['dissolution_date'],
    'putBackOn': ['dissolution_date'],
    'restoration': ['dissolution_date', 'restoration_expiry_date'],
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
