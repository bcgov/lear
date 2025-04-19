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
from datetime import datetime
from typing import Dict

from business_filer.exceptions import QueueException
from flask import current_app
from business_model.models import Business, PartyRole

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import create_party, create_role, update_director


def process(business: Business, filing: Dict, filing_meta: FilingMeta):  # pylint: disable=too-many-branches;
    """Render the change_of_directors onto the business model objects."""
    if not (new_directors := filing['changeOfDirectors'].get('directors')):
        return

    business.last_cod_date = filing_meta.application_date
    new_director_names = []

    for new_director in new_directors:  # pylint: disable=too-many-nested-blocks;
        # Applies only for filings coming from colin.
        if filing.get('colinIds'):
            director_found = False
            current_new_director_name = \
                new_director['officer'].get('firstName') + new_director['officer'].get('middleInitial', '') + \
                new_director['officer'].get('lastName')
            new_director_names.append(current_new_director_name.upper())

            for director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
                existing_director_name = \
                    director.party.first_name + director.party.middle_initial + director.party.last_name
                if existing_director_name.upper() == current_new_director_name.upper():
                    # Creates a new director record in Lear if a matching ceased director exists in Lear
                    # and the colin json contains the same director record with cessation date null.
                    if director.cessation_date is not None and new_director.get('cessationDate') is None:
                        director_found = False
                    else:
                        director_found = True
                        if new_director.get('cessationDate'):
                            new_director['actions'] = ['ceased']
                        else:
                            # For force updating address always as of now.
                            new_director['actions'] = ['modified']
                    break
            if not director_found:
                new_director['actions'] = ['appointed']

        if 'appointed' in new_director['actions']:

            # add new diretor party role to the business
            party = create_party(business_id=business.id, party_info=new_director)
            role = {
                'roleType': 'Director',
                'appointmentDate': new_director.get('appointmentDate'),
                'cessationDate': new_director.get('cessationDate')
            }
            new_director_role = create_role(party=party, role_info=role)
            business.party_roles.append(new_director_role)

        if any([action != 'appointed' for action in new_director['actions']]):  # pylint: disable=use-a-generator
            # get name of director in json for comparison *
            new_director_name = \
                new_director['officer'].get('firstName') + new_director['officer'].get('middleInitial', '') + \
                new_director['officer'].get('lastName') \
                if 'nameChanged' not in new_director['actions'] \
                else new_director['officer'].get('prevFirstName') + \
                new_director['officer'].get('prevMiddleInitial') + new_director['officer'].get('prevLastName')
            if not new_director_name:
                current_app.logger.error('Could not resolve director name from json %s.', new_director)
                raise QueueException

            for director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
                # get name of director in database for comparison *
                director_name = director.party.first_name + director.party.middle_initial + director.party.last_name
                # Update only an active director
                if director_name.upper() == new_director_name.upper() and director.cessation_date is None:
                    update_director(director=director, new_info=new_director)
                    break

    if filing.get('colinIds'):
        for director in PartyRole.get_parties_by_role(business.id, PartyRole.RoleTypes.DIRECTOR.value):
            # get name of director in database for comparison *
            director_name = director.party.first_name + director.party.middle_initial + director.party.last_name
            if director_name.upper() not in new_director_names and director.cessation_date is None:
                director.cessation_date = datetime.utcnow()
