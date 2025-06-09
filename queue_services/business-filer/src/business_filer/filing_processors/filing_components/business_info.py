# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Manages the type of Business."""
from datetime import UTC, datetime
from http import HTTPStatus

import requests
from business_model.models import Business, BusinessIdentifier, BusinessType, Filing, PartyRole
from flask import current_app
from flask_babel import _ as babel

from business_account.AccountService import AccountService
from business_filer.common.services import NaicsService
from business_filer.services import Flags


def set_corp_type(business: Business, business_info: dict) -> dict:
    """Set the legal type of the business."""
    if not business:
        return {"error": babel("Business required before type can be set.")}

    try:
        legal_type = business_info.get("legalType")
        if legal_type:
            business.legal_type = legal_type
    except (IndexError, KeyError, TypeError):
        return {"error": babel("A valid legal type must be provided.")}

    return None


def set_association_type(business: Business, association_type: str) -> dict:
    """Set the association type of business."""
    if not business:
        return {"error": babel("Business required before type can be set.")}

    try:
        cooperative_association_type = association_type
        if cooperative_association_type:
            business.association_type = cooperative_association_type
    except (IndexError, KeyError, TypeError):
        return {"error": babel("A valid association type must be provided.")}

    return None


def set_legal_name(corp_num: str,
                   business: Business,
                   business_info: dict,
                   new_legal_type: str | None = None):
    """Set the legal_name in the business object."""
    legal_name = business_info.get("legalName")
    if legal_name:
        business.legal_name = legal_name
    else:
        legal_type = new_legal_type or business_info.get("legalType")
        business.legal_name = Business.generate_numbered_legal_name(legal_type, corp_num)


def update_business_info(corp_num: str, business: Business, business_info: dict, filing: Filing):
    """Format and update the business entity from filing."""
    if corp_num and business and business_info and filing:
        set_legal_name(corp_num, business, business_info)
        business.identifier = corp_num
        business.legal_type = business_info.get("legalType")
        business.founding_date = filing.effective_date
        business.last_coa_date = filing.effective_date
        business.last_cod_date = filing.effective_date
        return business
    return None


def update_naics_info(business: Business, naics: dict):
    """Update naics info."""
    business.naics_code = naics.get("naicsCode")
    if business.naics_code:
        naics_structure = NaicsService.find_by_code(business.naics_code)
        business.naics_key = naics_structure["naicsKey"]
    else:
        business.naics_code = None
        business.naics_key = None
    business.naics_description = naics.get("naicsDescription")


def get_next_corp_num(legal_type: str, flags: Flags = None):
    """Retrieve the next available sequential corp-num from Lear or fallback to COLIN."""
    # this gets called if the new services are generating the Business.identifier.
    if legal_type in (Business.LegalTypes.BCOMP.value,
                      Business.LegalTypes.BC_ULC_COMPANY.value,
                      Business.LegalTypes.BC_CCC.value,
                      Business.LegalTypes.COMP.value):
        legal_type = "BC"
    elif legal_type in (Business.LegalTypes.BCOMP_CONTINUE_IN.value,
                        Business.LegalTypes.ULC_CONTINUE_IN.value,
                        Business.LegalTypes.CCC_CONTINUE_IN.value,
                        Business.LegalTypes.CONTINUE_IN.value):
        legal_type = "C"

    # when lear generating the identifier
    if (
        legal_type in (BusinessType.COOPERATIVE, BusinessType.PARTNERSHIP_AND_SOLE_PROP)
        or
        (Flags.is_on("enable-sandbox") and legal_type in (BusinessType.CORPORATION, BusinessType.CONTINUE_IN))
    ):
        if business_type := BusinessType.get_enum_by_value(legal_type):
            return BusinessIdentifier.next_identifier(business_type)
        return None

    # when colin generating the identifier
    try:
        token = AccountService.get_bearer_token()
        resp = requests.post(
            f'{current_app.config["COLIN_API"]}/businesses/{legal_type}',
            headers={"Accept": "application/json",
                     "Authorization": f"Bearer {token}"}
        )
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f'Failed to connect to {current_app.config["COLIN_API"]}')
        return None

    if resp.status_code == HTTPStatus.OK:
        new_corpnum = int(resp.json()["corpNum"])
        if new_corpnum and new_corpnum <= 9999999:  # noqa: PLR2004
            return f"{legal_type}{new_corpnum:07d}"
    return None


def get_firm_affiliation_passcode(business_id: int):
    """Return a firm passcode for a given business identifier."""
    pass_code = None
    end_date = datetime.now(UTC).date()
    party_roles = PartyRole.get_party_roles(business_id, end_date)

    if len(party_roles) == 0:
        return pass_code

    party = party_roles[0].party

    if party.party_type == "organization":
        pass_code = party.organization_name
    else:
        pass_code = party.last_name + ", " + party.first_name
        if hasattr(party, "middle_initial") and party.middle_initial:
            pass_code = pass_code + " " + party.middle_initial

    return pass_code
