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
    FILE_AM_AR = 'FILE_AM_AR'
    FILE_AM_LQ = 'FILE_AM_LQ'

    FILE_IAMGO = 'FILE_IAMGO'
    FILE_AMALO = 'FILE_AMALO'

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

    # Conversion Ledger
    FILE_CONVL = 'FILE_CONVL'

    # Conversion
    CONVAMAL_NULL = 'CONVAMAL_NULL'
    CONVCIN_NULL = 'CONVCIN_NULL'
    CONVCOUT_NULL = 'CONVCOUT_NULL'
    CONVDS_NULL = 'CONVDS_NULL'
    CONVDSF_NULL = 'CONVDSF_NULL'
    CONVDSL_NULL = 'CONVDSL_NULL'
    CONVDSO_NULL = 'CONVDSO_NULL'
    CONVICORP_NULL = 'CONVICORP_NULL'
    CONVID1_NULL = 'CONVID1_NULL'
    CONVID2_NULL = 'CONVID2_NULL'
    CONVILIQ_NULL = 'CONVILIQ_NULL'
    CONVLRSTR_NULL = 'CONVLRSTR_NULL'
    CONVNC_NULL = 'CONVNC_NULL'
    CONVRSTR_NULL = 'CONVRSTR_NULL'

    # Correction
    FILE_CO_AR = 'FILE_CO_AR'
    FILE_CO_BC = 'FILE_CO_BC'
    FILE_CO_DI = 'FILE_CO_DI'
    FILE_CO_DO = 'FILE_CO_DO'
    FILE_CO_LI = 'FILE_CO_LI'
    FILE_CO_LQ = 'FILE_CO_LQ'
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

    # TODO: Legacy Other - unsupported
    ADCORP_NULL = 'ADCORP_NULL'
    ADFIRM_NULL = 'ADFIRM_NULL'
    ADMIN_NULL = 'ADMIN_NULL'
    FILE_AM_TR = 'FILE_AM_TR'

    # TODO: Liquidation - unsupported
    # FILE_ADCOL = 'FILE_ADCOL'
    FILE_NOAPL = 'FILE_NOAPL'
    FILE_NOARM = 'FILE_NOARM'
    FILE_NOCAL = 'FILE_NOCAL'
    FILE_NOCDS = 'FILE_NOCDS'
    FILE_NOCEL = 'FILE_NOCEL'
    FILE_NOCER = 'FILE_NOCER'
    FILE_NOLDS = 'FILE_NOLDS'
    FILE_NOCRM = 'FILE_NOCRM'
    FILE_NOTRA = 'FILE_NOTRA'

    # TODO: Notice of Withdrawal - unsupported
    FILE_NWITH = 'FILE_NWITH'

    # Put Back Off
    SYSDL_NULL = 'SYSDL_NULL'
    FILE_AM_PF = 'FILE_AM_PF'
    FILE_CO_PF = 'FILE_CO_PF'

    # Put Back On
    FILE_AM_PO = 'FILE_AM_PO'
    FILE_CO_PO = 'FILE_CO_PO'

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
    # Adim Corp (ADCORP, BNUPD, ADMIN), XPRO filing
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
    EventFilings.FILE_AM_LQ: 'alteration',
    EventFilings.FILE_AM_RM: 'alteration',
    EventFilings.FILE_AM_SS: 'alteration',
    EventFilings.FILE_AM_AR: 'alteration',

    EventFilings.FILE_IAMGO: 'consentAmalgamationOut',
    EventFilings.FILE_AMALO: 'amalgamationOut',

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

    EventFilings.FILE_CONVL: 'conversionLedger',

    EventFilings.CONVAMAL_NULL: ['conversion', ('amalgamationApplication', 'unknown')],
    EventFilings.CONVCIN_NULL: ['conversion', 'continuationIn'],
    EventFilings.CONVCOUT_NULL: ['conversion', 'continuationOut'],
    EventFilings.CONVDS_NULL: ['conversion', ('dissolution', 'voluntary')],
    EventFilings.CONVDSF_NULL: ['conversion', ('dissolution', 'involuntary')],
    EventFilings.CONVDSL_NULL: 'conversion',  # TODO: liquidation
    EventFilings.CONVDSO_NULL: ['conversion', ('dissolution', 'unknown')],
    EventFilings.CONVICORP_NULL: 'conversion',
    EventFilings.CONVID1_NULL: ['conversion', 'putBackOn'],  # TODO: to confirm
    EventFilings.CONVID2_NULL: ['conversion', 'putBackOn'],  # TODO: to confirm
    EventFilings.CONVILIQ_NULL: 'conversion',  # TODO: liquidation
    EventFilings.CONVLRSTR_NULL: ['conversion', ('restoration', 'limitedRestoration')],
    EventFilings.CONVNC_NULL: ['conversion', 'changeOfName'],
    EventFilings.CONVRSTR_NULL: ['conversion', ('restoration', 'fullRestoration')],

    EventFilings.FILE_CO_AR: 'correction',
    EventFilings.FILE_CO_BC: 'correction',
    EventFilings.FILE_CO_DI: 'correction',
    EventFilings.FILE_CO_DO: 'correction',
    EventFilings.FILE_CO_LI: 'correction',
    EventFilings.FILE_CO_LQ: 'correction',
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

    # TODO: Legacy Other - unsupported
    EventFilings.ADCORP_NULL: 'legacyOther',
    EventFilings.ADFIRM_NULL: 'legacyOther',
    EventFilings.ADMIN_NULL: 'legacyOther',
    EventFilings.FILE_AM_TR: 'legacyOther',

    # TODO: Liquidation - unsupported
    EventFilings.FILE_NOAPL: 'appointLiquidator',
    EventFilings.FILE_NOARM: 'appointReceiver',
    EventFilings.FILE_NOCAL: 'changeLiquidatorAddress',
    EventFilings.FILE_NOCDS: 'changeRespectingDCR',
    EventFilings.FILE_NOCEL: 'ceaseLiquidator',
    EventFilings.FILE_NOCER: 'ceaseReceiver',
    EventFilings.FILE_NOLDS: 'locationDCR',
    EventFilings.FILE_NOCRM: 'changeReceiverAddress',
    EventFilings.FILE_NOTRA: 'transferRecordsOffice',

    EventFilings.FILE_NWITH: 'noticeOfWithdrawal',

    EventFilings.SYSDL_NULL: 'putBackOff',
    EventFilings.FILE_AM_PF: 'putBackOff',
    EventFilings.FILE_CO_PF: 'putBackOff',

    EventFilings.FILE_AM_PO: 'putBackOn',
    EventFilings.FILE_CO_PO: 'putBackOn',

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
    EventFilings.FILE_AM_LQ: 'Amendment - Liquidator',
    EventFilings.FILE_AM_RM: 'Amendment - Receiver or Receiver Manager',
    EventFilings.FILE_AM_SS: 'Amendment - Share Structure',
    EventFilings.FILE_AM_AR: 'Amendment - Annual Report',

    EventFilings.FILE_IAMGO: 'Application For Authorization For Amalgamation (into a Foreign Corporation) with 6 months consent granted',
    EventFilings.FILE_AMALO: 'Record of Amalgamation',

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

    EventFilings.FILE_NOCDR: 'Notice of Change of Directors', # dynamically add suffix for some scenarios
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
    EventFilings.FILE_CO_LQ: 'Correction - Liquidator',
    EventFilings.FILE_CO_RM: 'Correction - Receiver or Receiver Manager',
    EventFilings.FILE_CO_RR: 'Correction - Registered and Records Offices',
    EventFilings.FILE_CO_SS: 'Correction - Share Structure',
    EventFilings.FILE_CO_TR: 'Correction - Transition',
    EventFilings.FILE_CORRT: 'Correction',

    EventFilings.FILE_COURT: 'Court Order',

    # TODO: Delay of Dissolution - unsupported (need confirmation)
    # no ledger item in colin

    EventFilings.DISD1_DISDE: "Registrar's Notation - Dissolution or Cancellation Delay",  # has prefix "Registrar's Notation - "
    EventFilings.DISD2_DISDE: "Registrar's Notation - Dissolution or Cancellation Delay",

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

    # TODO: Legacy Other - unsupported
    EventFilings.ADCORP_NULL: None,
    EventFilings.ADFIRM_NULL: None,
    EventFilings.ADMIN_NULL: None,
    EventFilings.FILE_AM_TR: 'Amendment - Transition',

    # TODO: Liquidation - unsupported (need to check if anything missing)
    # NOLDS: "Notice of Location of Dissolved Company's Records"
    # LIQUR: 'Liquidation Report'
    # LQWOS: 'Notice of Withdrawal Statement of Intent to Liquidate'
    EventFilings.FILE_NOAPL: 'Notice of Appointment of Liquidator',
    EventFilings.FILE_NOARM: 'Notice of Appointment of Receiver or Receiver Manager',
    EventFilings.FILE_NOCAL: 'Notice of Change of Address of Liquidator And/Or Liquidation Records Office',
    EventFilings.FILE_NOCDS: 'Notice of Change Respecting Dissolved Company\'s Records',
    EventFilings.FILE_NOCEL: 'Notice of Ceasing to Act as Liquidator',
    EventFilings.FILE_NOCER: 'Notice of Ceasing to Act as Receiver or Receiver Manager',
    EventFilings.FILE_NOLDS: 'Notice of Location of Dissolved Company\'s Records',
    EventFilings.FILE_NOCRM: 'Notice of Change of Address of Receiver or Receiver Manager',
    EventFilings.FILE_NOTRA: 'Notice of Transfer of Records',
    # LQSIN: 'Statement of Intent to Liquidate'
    # LQSCO: 'Stay of Liquidation - Court Ordered'
    # LQDIS: 'Discontinuance of Liquidation - Court Ordered'
    # LQCON: 'Continuance of Liquidation - Court Ordered'
    # ADVLQ: 'Application for Dissolution (Voluntary Liquidation)'
    # AM_LR: 'Amendment - Liquidation Report'
    # CO_LR: 'Correction - Liquidation Report'

    EventFilings.FILE_NWITH: 'Notice of Withdrawal',

    EventFilings.SYSDL_NULL: None,
    EventFilings.FILE_AM_PF: 'Amendment - Put Back Off',
    EventFilings.FILE_CO_PF: 'Correction - Put Back Off',

    EventFilings.FILE_AM_PO: 'Amendment - Put Back On',
    EventFilings.FILE_CO_PO: 'Correction - Put Back On',

    EventFilings.FILE_REGSN: "Registrar's Notation",
    EventFilings.FILE_REGSO: "Registrar's Order",

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


SKIPPED_EVENT_FILE_TYPES = [
    # XPRO
    'FILE_CHGJU',
    'FILE_NWPTA',
    'FILE_PARES',
    'FILE_TILAT',
    'FILE_TILHO',
    'FILE_TILMA',
    'SYST_CANPS',
    'SYST_CHGJU',
    'SYST_CHGPN',
    'SYST_CO_PN',
    'SYST_LNKPS',
    'SYST_NWPTA',
    'SYST_PARES',
    'SYST_RIPFL',
    'SYST_TILAT',
    'SYST_TILHO',
    'SYST_NULL',
    'TRESP_NULL',
    'TRESP_COUTI',
    # Others
    'FILE_COGS1',
    # TODO: decide on the final list
]


NO_FILING_EVENT_FILE_TYPES = [
    'SYSD1_NULL',
    'SYSD2_NULL',
    # TODO: decide on the final list
]


LEAR_FILING_BUSINESS_UPDATE_MAPPING = {
    'incorporationApplication': ['last_coa_date', 'last_cod_date'],
    'changeOfAddress': ['last_coa_date'],
    'changeOfDirectors': ['last_cod_date'],
    'agmExtension': ['last_agm_date'],
    'amalgamationApplication': ['last_coa_date', 'last_cod_date'],
    'continuationIn': ['last_coa_date', 'last_cod_date'],
    'dissolution': ['dissolution_date'],
    'putBackOff': ['restoration_expiry_date', 'dissolution_date'],
    'putBackOn': ['dissolution_date'],
    'restoration': ['dissolution_date', 'restoration_expiry_date'],
}


LEAR_STATE_FILINGS = [
    'dissolution',
    'restoration',
    'putBackOff',
    'putBackOn',
    'continuationOut',
    'amalgamationOut',
    # TODO: other state filings that lear doesn't support for now e.g. liquidation

    # ingore the following since we won't map to them
    # 'dissolved', 'restorationApplication', 'continuedOut'
]


LEGAL_TYPE_CHANGE_FILINGS = {
    EventFilings.FILE_NOALB: ['ULC', 'BC'],
    EventFilings.FILE_NOALU: ['BC', 'ULC'],
    EventFilings.FILE_NOALC: ['BC', 'CC'],
}
