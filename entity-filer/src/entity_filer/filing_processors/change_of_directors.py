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
from legal_api.models import Address, Business, Director, Filing

from entity_filer.filing_processors import create_address, update_director
from entity_filer.service_utils import QueueException, logger


def process(business: Business, filing: Filing):
    """Render the change_of_directors onto the business model objects."""
    new_directors = filing['changeOfDirectors'].get('directors')

    for new_director in new_directors:
        if 'appointed' in new_director['actions']:
            # create address
            address = create_address(new_director['deliveryAddress'], Address.DELIVERY)

            director_to_add = Director(first_name=new_director['officer'].get('firstName', '').upper(),
                                               middle_initial=new_director['officer'].get('middleInitial', '').upper(),
                                               last_name=new_director['officer'].get('lastName', '').upper(),
                                               title=new_director.get('title', '').upper(),
                                               appointment_date=new_director.get('appointmentDate'),
                                               cessation_date=new_director.get('cessationDate'),
                                               delivery_address=address)

            if ('mailingAddress' in new_director.keys()):
                mailing_address = create_address(new_director['mailingAddress'], Address.MAILING)
                director_to_add.mailing_address = mailing_address

            # add new director to the list
            business.directors.append(director_to_add)

        if any([action != 'appointed' for action in new_director['actions']]):
            # get name of director in json for comparison *
            new_director_name = \
                new_director['officer'].get('firstName') + new_director['officer'].get('middleInitial') + \
                new_director['officer'].get('lastName') \
                if 'nameChanged' not in new_director['actions'] \
                else new_director['officer'].get('prevFirstName') + \
                new_director['officer'].get('prevMiddleInitial') + new_director['officer'].get('prevLastName')
            if not new_director_name:
                logger.error('Could not resolve director name from json %s.', new_director)
                raise QueueException

            for director in business.directors:
                # get name of director in database for comparison *
                director_name = director.first_name + director.middle_initial + director.last_name
                if director_name.upper() == new_director_name.upper():
                    update_director(director, new_director)
                    break
