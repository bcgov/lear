from enum import Enum


class DocumentClasses(Enum):
    """Render an Enum of the document service document classes."""

    COOP = "COOP"
    CORP = "CORP"
    FIRM = "FIRM"


class DocumentTypes(Enum):
    """Render an Enum of the document service document types."""
    # COOP 
    COFI = "COFI"                               # Correction Filing
    COOP_MEMORANDUM = "COOP_MEMORANDUM"         # Cooperative Memorandum
    COOP_MISC = "COOP_MISC"                     # Cooperatives miscellaneous documents
    COOP_RULES = "COOP_RULES"                   # Cooperative Rules

    # CORP
    AMAL = "AMAL"                               # Update Due to Amalgamation
    AMLG = "AMLG"                               # Amalgamations
    AMLO = "AMLO"                               # Amalgamation Out
    ANNR = "ANNR"                               # Annual Report
    APCO = "APCO"                               # Application to Correct the Registry
    ASNU = "ASNU"                               # Assumed Name Undertaking
    ATTN = "ATTN"                               # Attorney
    CERT = "CERT"                               # Certificates
    CLW = "CLW"                                 # Client Letters
    CNTA = "CNTA"                               # Continuation in Authorization
    CNTI = "CNTI"                               # Continuation In
    CNTO = "CNTO"                               # Continuation Out
    CNVS = "CNVS"                               # Conversions
    COFF = "COFF"                               # CORPS Filed Forms
    COMP = "COMP"                               # CERTIFICATE OF COMPANIES
    CORC = "CORC"                               # Corrections
    CORP_AFFIDAVIT = "CORP_AFFIDAVIT"           # Affidavit
    CORP_MISC = "CORP_MISC"                     # Corporations miscellaneous documents
    COSD = "COSD"                               # CORPS Supporting Documentation
    COU = "COU"                                 # INACTIVE/DEPRECATED Court Order
    CRT = "CRT"                                 # INACTIVE/DEPRECATED Court Order
    CRTO = "CRTO"                               # Court Orders
    DIRECTOR_AFFIDAVIT = "DIRECTOR_AFFIDAVIT"   # Director Affidavit
    DIRS = "DIRS"                               # Directors
    DISD = "DISD"                               # Dissolution Delays
    INV = "INV"                                 # INACTIVE/DEPRECATED Investigation
    FRMA = "FRMA"                               # Form 2's Address Change for Corps
    LTR = "LTR"                                 # Letter Templates
    MNOR = "MNOR"                               # Minister's Order
    NATB = "NATB"                               # INACTIVE/DEPRECATED Nature of Business
    PLNA = "PLNA"                               # Plan of Arrangements
    REGN = "REGN"                               # Registrar's Notation
    REGO = "REGO"                               # Registrar's Order
    RSRI = "RSRI"                               # Restoration/Reinstatement
    SUPP = "SUPP"                               # Supporting Documents
    SYSR = "SYSR"                               # System is the record

    # FIRM
    CNVF = "CNVF"                               # Conversion of Firm
    COPN = "COPN"                               # Change of Proprietor's Name
    DISS = "DISS"                               # Dissolution Due to Death
    FIRM_MISC = "FIRM_MISC"                     # Firms miscellaneous documents
    PART = "PART"                               # Partnerships

    # common
    ADDR = "ADDR"                               # Address CORP/FIRM
    CONT = "CONT"                               # Consent | COOP/CORP/FIRM
    CORR = "CORR"                               # Correspondence | COOP/CORP/FIRM
    FILE = "FILE"                               # COLIN Filing | COOP/CORP/FIRM

# Map between filing and DRS document type
# SYSR: alteration, appointReceiver, ceaseReceiver, changeOfDirectors,
# incorporationApplication, restoration, noticeOfWithdrawal
DOCUMENT_TYPES = {  
    "amalgamationApplication": DocumentTypes.AMLG.value,
    "amalgamationOut": DocumentTypes.AMLO.value,
    "annualReport": DocumentTypes.ANNR.value,
    "changeOfAddress": DocumentTypes.FRMA.value,
    "continuationIn": DocumentTypes.CNTI.value,
    "continuationOut": DocumentTypes.CNTO.value,
    "conversion": {
        DocumentClasses.CORP.value: DocumentTypes.CNVS.value,
        DocumentClasses.FIRM.value: DocumentTypes.CNVF.value
    },
    "correction": DocumentTypes.CORC.value,
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
