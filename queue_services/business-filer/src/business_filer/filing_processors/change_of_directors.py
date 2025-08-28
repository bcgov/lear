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
"""File processing rules and actions for the change of directors."""
import copy
from datetime import UTC, datetime

from business_model.models import Business, Filing, PartyRole
from flask import current_app

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import create_party, create_role, update_director


def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):  # noqa: PLR0912
    """Render the change_of_directors onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)
    if not (directors := filing_json["filing"]["changeOfDirectors"].get("directors")):
        return

    business.last_cod_date = filing_meta.application_date
    colin_director_names = []
    new_directors = []

    for director in directors:  # pylint: disable=too-many-nested-blocks;
        # Applies only for filings coming from colin.
        if filing_rec.colin_event_ids:
            director_found = False
            director_name = (director["officer"].get("firstName") +
                             director["officer"].get("middleInitial", "") +
                             director["officer"].get("lastName"))
            colin_director_names.append(director_name.upper())

            for current_director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
                current_director_name = (current_director.party.first_name +
                                         current_director.party.middle_initial +
                                         current_director.party.last_name)
                if current_director_name.upper() == director_name.upper():
                    # Creates a new director record in Lear if a matching ceased director exists in Lear
                    # and the colin json contains the same director record with cessation date null.
                    if current_director.cessation_date is not None and director.get("cessationDate") is None:
                        director_found = False
                    else:
                        director_found = True
                        if director.get("cessationDate"):
                            director["actions"] = ["ceased"]
                        else:
                            # For force updating address always as of now.
                            director["actions"] = ["addressChanged"]
                    break
            if not director_found:
                director["actions"] = ["appointed"]

            filing_rec._filing_json = filing_json  # pylint: disable=protected-access; bypass to update filing json

        if "appointed" in director["actions"]:
            new_directors.append(director)

        elif any([action != "appointed" for action in director["actions"]]):  # noqa: C419
            # get name of director in json for comparison *
            if "nameChanged" in director["actions"]:
                director_name = (director["officer"].get("prevFirstName") +
                                 director["officer"].get("prevMiddleInitial", "") +
                                 director["officer"].get("prevLastName"))
            else:
                director_name = (director["officer"].get("firstName") +
                                 director["officer"].get("middleInitial", "") +
                                 director["officer"].get("lastName"))
            if not director_name:
                current_app.logger.error("Could not resolve director name from json %s.", director)
                raise QueueException

            for current_director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
                # get name of director in database for comparison *
                current_director_name = (current_director.party.first_name +
                                         current_director.party.middle_initial +
                                         current_director.party.last_name)
                # Update only an active director
                if current_director_name.upper() == director_name.upper() and current_director.cessation_date is None:
                    update_director(director=current_director, new_info=director)
                    break

    for director in new_directors:        
        # add new diretor party role to the business
        party = create_party(business_id=business.id, party_info=director)
        role = {
            "roleType": "Director",
            "appointmentDate": director.get("appointmentDate"),
            "cessationDate": director.get("cessationDate")
        }
        new_director_role = create_role(party=party, role_info=role)
        business.party_roles.append(new_director_role)

    if filing_rec.colin_event_ids:
        for current_director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
            # get name of director in database for comparison *
            current_director_name = (current_director.party.first_name +
                                     current_director.party.middle_initial +
                                     current_director.party.last_name)
            if current_director_name.upper() not in colin_director_names and current_director.cessation_date is None:
                current_director.cessation_date = datetime.now(UTC)
