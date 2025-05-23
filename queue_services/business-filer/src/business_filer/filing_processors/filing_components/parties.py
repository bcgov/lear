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
"""Manages the parties and party roles for a business."""
from __future__ import annotations

from business_model.models import Business, Filing, PartyRole

from business_filer.filing_processors.filing_components import create_party, create_role


def update_parties(business: Business, parties_structure: dict, filing: Filing, delete_existing=True) -> list | None:
    """Manage the party and party roles for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    if parties_structure:
        if delete_existing:
            try:
                delete_parties(business)
            except:
                err.append(
                    {"error_code": "FILER_UNABLE_TO_DELETE_PARTY_ROLES",
                     "error_message": f"Filer: unable to delete party roles for :'{business.identifier}'"}
                )
                return err

        try:
            for party_info in parties_structure:
                party = create_party(business_id=business.id, party_info=party_info, create=False)
                for role_type in party_info.get("roles"):
                    role_str = role_type.get("roleType", "").lower()
                    role = {
                        "roleType": role_str,
                        "appointmentDate": role_type.get("appointmentDate", None),
                        "cessationDate": role_type.get("cessationDate", None)
                    }
                    party_role = create_role(party=party, role_info=role)
                    if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value,
                                           PartyRole.RoleTypes.INCORPORATOR.value,
                                           PartyRole.RoleTypes.APPLICANT.value]:
                        filing.filing_party_roles.append(party_role)
                    else:
                        business.party_roles.append(party_role)
        except KeyError:
            err.append(
                {"error_code": "FILER_UNABLE_TO_SAVE_PARTIES",
                 "error_message": f"Filer: unable to save new parties for :'{business.identifier}'"}
            )
    return err


def delete_parties(business: Business):
    """Delete the party_roles for a business."""
    if existing_party_roles := business.party_roles.all():
        for role in existing_party_roles:
            if role.role not in [
                PartyRole.RoleTypes.OFFICER.value,
                PartyRole.RoleTypes.RECEIVER.value,
                PartyRole.RoleTypes.LIQUIDATOR.value,
            ]:
                business.party_roles.remove(role)
