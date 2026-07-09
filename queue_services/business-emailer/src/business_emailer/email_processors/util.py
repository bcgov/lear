# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Email processing utilities and shared constants."""
from business_model.models import Business

FILING_TITLE = {
    "alteration": "Alteration",
    "amalgamationApplication": "Amalgamation Application",
    "annualReport": "Annual Report",
    "changeOfDirectors": "Director Change",
    "changeOfAddress": "Address Change",
    "changeOfRegistration": "Change of Registration",
    "continuationIn": "Continuation Application",
    "incorporationApplication": "Incorporation Application",
    "registration": "Registration",
    "specialResolution": "Special Resolution",
    "restoration": "Restoration"
}

FILING_TITLE_SHORT = {
    "amalgamationApplication": "Amalgamation",
    "continuationIn": "Continuation In",
    "incorporationApplication": "Incorporation",
    "restoration": {
        "fullRestoration": "Restoration",
        "limitedRestoration": "Restoration",
        "limitedRestorationExtension": "Extension of Limited Restoration",
        "limitedRestorationToFull": "Conversion to Full Restoration",
    }
}

FILING_ATTACHMENTS = {
    "CP": {
        "annualReport": {
            "attachments": ["Annual Report","Receipt"],
            "extraPdfTypes": [],
        },
        "changeOfAddress": {
            "attachments": ["Address Change","Receipt"],
            "extraPdfTypes": [],
        },
        "changeOfDirectors": {
            "attachments": ["Director Change","Receipt"],
            "extraPdfTypes": [],
        },
        "incorporationApplication": {
            "attachments": ["Incorporation Application","Certificate of Incorporation","Certified Rules","Memorandum","Receipt"],
            "extraPdfTypes": ["certificateOfIncorporation","certifiedRules","certifiedMemorandum"],
        },
        "specialResolution": {
            "attachments": ["Special Resolution","Special Resolution Application","Certificate of Name Change","Certified Rules","Receipt"],
            "extraPdfTypes": ["specialResolutionApplication","certificateOfNameChange","certifiedRules"],
        },
    },
    "CORP": {
        "alteration": {
            "attachments": ["Alteration","Notice of Articles","Certificate of Name Change","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfNameChange"],
        },
        "amalgamationApplication-horizontal": {
            "attachments": ["Amalgamation Application Short-form (Horizontal)","Notice of Articles","Certificate of Amalgamation","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfAmalgamation"],
        },
        "amalgamationApplication-regular": {
            "attachments": ["Amalgamation Application (Regular)","Notice of Articles","Certificate of Amalgamation","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfAmalgamation"],
        },
        "amalgamationApplication-vertical": {
            "attachments": ["Amalgamation Application Short-form (Vertical)","Notice of Articles","Certificate of Amalgamation","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfAmalgamation"],
        },
        "annualReport": {
            "attachments": ["Annual Report","Receipt"],
            "extraPdfTypes": [],
        },
        "changeOfAddress": {
            "attachments": ["Address Change","Notice of Articles","Receipt"],
            "extraPdfTypes": ["noticeOfArticles"],
        },
        "changeOfDirectors": {
            "attachments": ["Director Change","Notice of Articles","Receipt"],
            "extraPdfTypes": ["noticeOfArticles"],
        },
        "continuationIn": {
            "attachments": ["Continuation Application","Notice of Articles","Certificate of Continuation","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfContinuation"],
        },
        "incorporationApplication": {
            "attachments": ["Incorporation Application","Notice of Articles","Certificate of Incorporation","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfIncorporation"],
        },
        "restoration-fullRestoration": {
            "attachments": ["Full Restoration Application","Notice of Articles","Certificate of Restoration","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfRestoration"],
        },
        "restoration-limitedRestoration": {
            "attachments": ["Limited Restoration Application","Notice of Articles","Certificate of Restoration","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfRestoration"],
        },
        "restoration-limitedRestorationExtension": {
            "attachments": ["Limited Restoration Extension Application","Notice of Articles","Certificate of Restoration","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfRestoration"],
        },
        "restoration-limitedRestorationToFull": {
            "attachments": ["Conversion to Full Restoration Application","Notice of Articles","Certificate of Restoration","Receipt"],
            "extraPdfTypes": ["noticeOfArticles","certificateOfRestoration"],
        }
    },
    "FIRM": {
        "changeOfRegistration": {
            "attachments": ["Change of Registration", "Amended Registration Statement", "Receipt"],
            "extraPdfTypes": ["amendedRegistrationStatement"],
        },
        "registration": {
            "attachments": ["Statement of Registration","Receipt"],
            "extraPdfTypes": [],
        }
    }
}

OFFICE_NAME = {
    "CP": "registered office",
    "CORP": "registered office",
    "FIRM": "business"
}

NOT_AVAILABLE = "Not Available"


def get_legal_type_key(legal_type: str) -> str:
    """Get the key for the legal type."""
    if legal_type == Business.LegalTypes.COOP.value:
        return "CP"
    elif legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        return "FIRM"
    return "CORP"