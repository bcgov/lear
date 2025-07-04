from enum import Enum


class DocumentClasses(Enum):
    """Render an Enum of the document service document classes."""

    COOP = "COOP"
    CORP = "CORP"
    DELETED = "DELETED"
    FIRM = "FIRM"
    LP_LLP = "LP_LLP"
    MHR = "MHR"
    NR = "NR"
    OTHER = "OTHER"
    PPR = "PPR"
    SOCIETY = "SOCIETY"
    XP = "XP"


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


# Map between filing and DRS document type
# SYSR: alteration, appointReceiver, ceaseReceiver, changeOfDirectors,
# incorporationApplication, restoration, noticeOfWithdrawal
DOCUMENT_TYPES = {
    "affidavit": {"class": DocumentClasses.SOCIETY.value, "type": DocumentTypes.AFDV.value},
    "amalgamationApplication": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.AMLG.value},
    "amalgamationOut": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.AMLO.value},
    "annualReport": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.ANNR.value},
    "changeOfAddress": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.FRMA.value},
    "consentAmalgamationOut": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.AMLO.value},
    "consentContinuationOut": {"class": DocumentClasses.CORP.value, "TYPE": DocumentTypes.CNTO.value},
    "continuationIn": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.CNTI.value},
    "continuationOut": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.CNTO.value},
    "conversion": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.CNVS.value},
    "correction": {"class": DocumentClasses.COOP.value, "type": DocumentTypes.CORR.value},
    "courtOrder": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.CRT.value},
    "registrarsNotation": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.REGN.value},
    "registrarsOrder": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.REGO.value},
    "systemIsTheRecord": {"class": DocumentClasses.CORP.value, "type": DocumentTypes.SYSR.value},
    "incorporationApplication": {"class": DocumentClasses.COOP.value},
}
