# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Constants for legal api."""

from enum import Enum


BOB_DATE = '2019-03-08'

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

    REG_101 = "REG_101"
    REG_102 = "REG_102"
    REG_103 = "REG_103"
    ABAN = "ABAN"
    ADDI = "ADDI"
    AFFE = "AFFE"
    ATTA = "ATTA"
    BANK = "BANK"
    BCLC = "BCLC"
    CAU = "CAU"
    CAUC = "CAUC"
    CAUE = "CAUE"
    COMP = "COMP"
    COUR = "COUR"
    DEAT = "DEAT"
    DNCH = "DNCH"
    EXMN = "EXMN"
    EXNR = "EXNR"
    EXRE = "EXRE"
    EXRS = "EXRS"
    FORE = "FORE"
    FZE = "FZE"
    GENT = "GENT"
    LETA = "LETA"
    MAID = "MAID"
    MAIL = "MAIL"
    MARR = "MARR"
    NAMV = "NAMV"
    NCAN = "NCAN"
    NCON = "NCON"
    NPUB = "NPUB"
    NRED = "NRED"
    PDEC = "PDEC"
    PUBA = "PUBA"
    REBU = "REBU"
    REGC = "REGC"
    REIV = "REIV"
    REPV = "REPV"
    REST = "REST"
    STAT = "STAT"
    SZL = "SZL"
    TAXN = "TAXN"
    TAXS = "TAXS"
    THAW = "THAW"
    TRAN = "TRAN"
    VEST = "VEST"
    WHAL = "WHAL"
    WILL = "WILL"
    XP_MISC = "XP_MISC"
    COFI = "COFI"
    DISS = "DISS"
    DISD = "DISD"
    ATTN = "ATTN"
    FRMA = "FRMA"
    AMLO = "AMLO"
    CNTA = "CNTA"
    CNTI = "CNTI"
    CNTO = "CNTO"
    COFF = "COFF"
    COSD = "COSD"
    AMLG = "AMLG"
    AMAL = "AMAL"
    RSRI = "RSRI"
    ASNU = "ASNU"
    LPRG = "LPRG"
    FILE = "FILE"
    CNVF = "CNVF"
    COPN = "COPN"
    MHSP = "MHSP"
    FNCH = "FNCH"
    CONS = "CONS"
    PPRS = "PPRS"
    PPRC = "PPRC"
    ADDR = "ADDR"
    ANNR = "ANNR"
    CORR = "CORR"
    DIRS = "DIRS"
    CORC = "CORC"
    SOCF = "SOCF"
    CERT = "CERT"
    LTR = "LTR"
    CLW = "CLW"
    BYLW = "BYLW"
    CNST = "CNST"
    CONT = "CONT"
    SYSR = "SYSR"
    ADMN = "ADMN"
    RSLN = "RSLN"
    AFDV = "AFDV"
    SUPP = "SUPP"
    MNOR = "MNOR"
    FINM = "FINM"
    APCO = "APCO"
    RPTP = "RPTP"
    DAT = "DAT"
    BYLT = "BYLT"
    CNVS = "CNVS"
    CRTO = "CRTO"
    MEM = "MEM"
    PRE = "PRE"
    REGO = "REGO"
    PLNA = "PLNA"
    REGN = "REGN"
    FINC = "FINC"
    BCGT = "BCGT"
    CHNM = "CHNM"
    OTP = "OTP"
    PPR = "PPR"
    LHS = "LHS"
    RGS = "RGS"
    HSR = "HSR"
    RPL = "RPL"
    FINS = "FINS"
    DELETED = "DELETED"
    COOP_RULES = "COOP_RULES"
    COOP_MEMORANDUM = "COOP_MEMORANDUM"
    CORP_AFFIDAVIT = "CORP_AFFIDAVIT"
    DIRECTOR_AFFIDAVIT = "DIRECTOR_AFFIDAVIT"
    PART = "PART"
    REG_103E = "REG_103E"
    AMEND_PERMIT = "AMEND_PERMIT"
    CANCEL_PERMIT = "CANCEL_PERMIT"
    REREGISTER_C = "REREGISTER_C"
    MEAM = "MEAM"
    COU = "COU"
    CRT = "CRT"
    INV = "INV"
    NATB = "NATB"
    NWP = "NWP"

DOCUMENT_TYPES = {
    'coopMemorandum': {
        'class': DocumentClasses.COOP.value,
        'type': DocumentTypes.COOP_MEMORANDUM.value
    },
    'coopRules': {
        'class': DocumentClasses.COOP.value,
        'type': DocumentTypes.COOP_RULES.value
    },
}
