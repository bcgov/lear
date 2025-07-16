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
    "SP": DocumentClasses.FIRM.value,
    "GP": DocumentClasses.FIRM.value,
}

# Matches IDs starting with 'DS' followed by at least 10 digits
DRS_ID_PATTERN = r"^DS\d{10,}$"
