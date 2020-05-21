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
"""File processing rules and actions for the change of directors."""
from datetime import datetime
from typing import Dict

from entity_queue_common.service_utils import QueueException, logger
from legal_api.models import Business, PartyRole

from entity_filer.filing_processors import create_party, create_role, update_director


def process(business: Business, filing: Dict):  # pylint: disable=too-many-branches;
    """Render the change_of_directors onto the business model objects."""
    new_directors = filing['changeOfDirectors'].get('directors')
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

        if any([action != 'appointed' for action in new_director['actions']]):
            # get name of director in json for comparison *
            new_director_name = \
                new_director['officer'].get('firstName') + new_director['officer'].get('middleInitial', '') + \
                new_director['officer'].get('lastName') \
                if 'nameChanged' not in new_director['actions'] \
                else new_director['officer'].get('prevFirstName') + \
                new_director['officer'].get('prevMiddleInitial') + new_director['officer'].get('prevLastName')
            if not new_director_name:
                logger.error('Could not resolve director name from json %s.', new_director)
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
