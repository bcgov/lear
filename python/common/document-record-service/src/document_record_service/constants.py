from enum import Enum


class DocumentClasses(Enum):
    """Render an Enum of the document service document classes."""

    COOP = "COOP"
    CORP = "CORP"
    FIRM = "FIRM"


class DocumentTypes(Enum):
    """Render an Enum of the document service document types."""

    AFDV = "AFDV"
    AMLG = "AMLG"
    ANNR = "ANNR"
    FRMA = "FRMA"
    AMLO = "AMLO"
    CNTO = "CNTO"
    CNTI = "CNTI"
    CNVS = "CNVS"
    CORR = "CORR"
    CRT = "CRT"
    CORP = "CORP"
    REGN = "REGN"
    REGO = "REGO"
    SYSR = "SYSR"
    FZE_ADMIN = 'FZE_ADMIN'
    AGMEX = 'AGMEX'
    NOALA = 'NOALA'
    AGMLC = 'AGMLC'
    AGMAM = 'AGMAM'
    RECV_APPOINT = 'RECV_APPOINT'
    RECV_CEASE = 'RECV_CEASE'
    CHANGE_NAME = 'CHANGE_NAME'
    CHANGE_OFF = 'CHANGE_OFF'
    CHANGE_REG = 'CHANGE_REG'
    CNV_LEDGER = 'CNV_LEDGER'
    CRTO_LIQ = 'CRTO_LIQ'
    DISS_VOL = 'DISS_VOL'
    DISS_ADMIN = 'DISS_ADMIN'
    ICORP = 'ICORP'
    CORP_AFFIDAVIT = 'CORP_AFFIDAVIT'
    COMP = 'COMP'
    INTENT_LIQ = 'INTENT_LIQ'
    OTHER_LEGACY = 'OTHER_LEGACY'
    NWITH = 'NWITH'
    PB_OFF = 'PB_OFF'
    PB_ON = 'PB_ON'
    REG_BUS = 'REG_BUS'
    RSLN_SPEC = 'RSLN_SPEC'
    TRANSP_REG = 'TRANSP_REG'
    # FIRM
    ADDR = 'ADDR'
    CNVF = 'CNVF'
    CONT = 'CONT'
    COPN = 'COPN'
    CORR = 'CORR'
    DISS = 'DISS'
    FILE = 'FILE'
    FIRM_MISC = 'FIRM_MISC'
    PART = 'PART'


# Map between filing and DRS document type
# SYSR: alteration, appointReceiver, ceaseReceiver, changeOfDirectors,
# incorporationApplication, restoration, noticeOfWithdrawal
DOCUMENT_TYPES = {
    "amalgamationApplication": DocumentTypes.AMLG.value,
    "amalgamationOut": DocumentTypes.AMLO.value,
    "annualReport": DocumentTypes.ANNR.value,
    "changeOfAddress": DocumentTypes.FRMA.value,
    "consentAmalgamationOut": DocumentTypes.AMLO.value,
    "consentContinuationOut": DocumentTypes.CNTO.value,
    "continuationIn": DocumentTypes.CNTI.value,
    "continuationOut": DocumentTypes.CNTO.value,
    "conversion": DocumentTypes.CNVS.value,
    "correction": DocumentTypes.CORR.value,
    "courtOrder": DocumentTypes.CRT.value,
    "registrarsNotation": DocumentTypes.REGN.value,
    "registrarsOrder": DocumentTypes.REGO.value,
    "systemIsTheRecord": DocumentTypes.SYSR.value,
}

# Map between legal type and DRS document class
# For all other legal types not listed below, the document class defaults to CORP
DOCUMENT_CLASSES = {
    "CP": DocumentClasses.COOP.value,
    "XCP": DocumentClasses.COOP.value,
    "SP": DocumentClasses.FIRM.value,
    "GP": DocumentClasses.FIRM.value,
}

# Matches IDs starting with 'DS' followed by at least 10 digits
DRS_ID_PATTERN = r"^DS\d{10,}$"
