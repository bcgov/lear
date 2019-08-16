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
import pycountry

from entity_filer.filing_processors import create_address
from legal_api.models import Address, Business, Director, Filing


def process(business: Business, filing: Filing):
    """Render the change_of_directors onto the business model objects."""
    new_directors = filing['changeOfDirectors'].get('directors')

    for new_director in new_directors:
        existing_dir = False
        for director in business.directors:
            director_name = director.first_name + director.middle_initial + director.last_name
            new_director_name = \
                new_director['officer'].get('firstName') + new_director['officer'].get('middleInitial') +\
                new_director['officer'].get('lastName')

            if director_name == new_director_name:
                # mark director as existing from before
                existing_dir = True

                # set cessation date if given
                director.cessation_date = new_director.get('cessationDate')

                # check for address change
                new_address = create_address(new_director['deliveryAddress'], Address.DELIVERY)
                for key in new_address.json:
                    # if any change in address then update the address to the new one
                    if new_address.json[key] != director.delivery_address.json[key]:
                        director.delivery_address = new_address
                        break

        if not existing_dir:
            # create address
            address = create_address(new_director['deliveryAddress'], Address.DELIVERY)

            # add new director to the list
            business.directors.append(Director(first_name=new_director['officer'].get('firstName'),
                                               middle_initial=new_director['officer'].get('middleInitial'),
                                               last_name=new_director['officer'].get('lastName'),
                                               title=new_director.get('title'),
                                               appointment_date=new_director.get('appointmentDate'),
                                               cessation_date=new_director.get('cessationDate'),
                                               delivery_address=address))
