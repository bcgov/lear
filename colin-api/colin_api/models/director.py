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
"""Meta information about the service.

Currently this only provides API versioning information
"""
import datetime

from flask import current_app

from colin_api.exceptions import DirectorsNotFoundException
from colin_api.models import Address
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date


class Director:
    """Director object."""

    officer = None
    delivery_address = None
    # mailing_address = None
    title = None
    appointment_date = None
    cessation_date = None
    start_event_id = None
    end_event_id = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'officer': self.officer,
            'deliveryAddress': self.delivery_address,
            # 'mailingAddress': self.mailing_address,
            'title': self.title,
            'appointmentDate': self.appointment_date,
            'cessationDate': self.cessation_date,
            'startEventId': self.start_event_id,
            'endEventId': self.end_event_id,
            'actions': []
        }

    @classmethod
    def get_current(cls, identifier: str = None):
        """Return current directors for given identifier."""
        if not identifier:
            return None

        try:
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select first_nme, middle_nme, last_nme, delivery_addr_id, appointment_dt, cessation_dt, start_event_id,
                end_event_id
                from corp_party
                where end_event_id is NULL and corp_num=:identifier and party_typ_cd='DIR'
                """,
                identifier=identifier
            )
            directors_list = cls._build_directors_list(cursor)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting current directors info for {}'.format(identifier))
            raise err

        if not directors_list:
            raise DirectorsNotFoundException(identifier=identifier)

        return directors_list

    @classmethod
    def get_by_event(cls, identifier: str = None, event_id: int = None):
        """Get all directors active or deleted during this event."""
        if not event_id:
            return None

        try:
            cursor = DB.connection.cursor()
            cursor.execute(
                """
                select first_nme, middle_nme, last_nme, delivery_addr_id, appointment_dt, cessation_dt, start_event_id,
                end_event_id
                from corp_party
                where ((start_event_id<=:event_id and end_event_id is null) or (start_event_id<=:event_id and
                cessation_dt is not null and end_event_id>=:event_id) or (start_event_id<:event_id and
                end_event_id>:event_id)) and party_typ_cd='DIR' and corp_num=:identifier
                """,
                event_id=event_id,
                identifier=identifier
            )

            directors_list = cls._build_directors_list(cursor, event_id)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting directors info for event {}'.format(event_id))
            raise err

        if not directors_list:
            raise DirectorsNotFoundException(event_id=event_id)

        return directors_list

    @classmethod
    def end_current(cls, cursor, event_id: int = None, corp_num: str = None):
        """Set all end_event_ids for current directors."""
        if not event_id:
            current_app.logger.error('Error in director: No event id given to end current directors.')

        try:
            cursor.execute("""
                update corp_party set end_event_id=:event_id where corp_num=:corp_num and end_event_id is null""",
                           event_id=event_id,
                           corp_num=corp_num
                           )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end current directors for event {event_id}')
            raise err

    @classmethod
    def end_by_name(cls, cursor, director: dict = None, event_id: int = None, corp_num: str = None):
        """Set all end_event_ids for given directors."""
        if not director:
            current_app.logger.error('Error in director: No director given to end.')

        if not event_id:
            current_app.logger.error('Error in director: No event id given to end director.')

        officer = director['officer']
        first_name = officer['prevFirstName'] if 'nameChanged' in director['actions'] else officer['firstName']
        last_name = officer['prevLastName'] if 'nameChanged' in director['actions'] else officer['lastName']
        middle_initial = officer.get('prevMiddleInitial', '') if 'nameChanged' in director['actions'] \
            else officer.get('middleInitial', '')

        try:
            cursor.execute(
                """
                update corp_party set end_event_id=:event_id, cessation_dt=TO_DATE(:cessation_date, 'YYYY-mm-dd') where
                corp_num=:corp_num and trim(first_nme)=:first_name and trim(last_nme)=:last_name and
                (trim(middle_nme)=:middle_initial or middle_nme is null)
                """,
                event_id=event_id,
                cessation_date=director.get('cessationDate', ''),
                corp_num=corp_num,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                middle_initial=middle_initial.strip()
            )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end director: {director}')
            raise err

    @classmethod
    def create_new_director(cls, cursor, event_id: int = None, director: dict = None, business: dict = None):
        """Insert new director into the corp_party table."""
        if not event_id:
            current_app.logger.error('Error in director: No event id given to create director.')
        if not director:
            current_app.logger.error('Error in director: No director data given to create director.')

        # validate appointment + cessation dates

        # create new address
        addr_id = Address.create_new_address(cursor=cursor, address_info=director['deliveryAddress'])

        # create new corp party entry
        try:
            cursor.execute("""select noncorp_party_seq.NEXTVAL from dual""")
            row = cursor.fetchone()
            corp_party_id = int(row[0])
        except Exception as err:
            current_app.logger.error('Error in director: Failed to get next corp_party_id.')
            raise err
        try:
            cursor.execute("""
                insert into corp_party (corp_party_id, mailing_addr_id, delivery_addr_id, corp_num, party_typ_cd,
                start_event_id, end_event_id, appointment_dt, cessation_dt, last_nme, middle_nme, first_nme,
                business_nme, bus_company_num)
                values (:corp_party_id, :mailing_addr_id, :delivery_addr_id, :corp_num, :party_typ_cd, :start_event_id,
                :end_event_id, TO_DATE(:appointment_dt, 'YYYY-mm-dd'), TO_DATE(:cessation_dt, 'YYYY-mm-dd'), :last_nme,
                :middle_nme, :first_nme, :business_nme, :bus_company_num)
                """,
                           corp_party_id=corp_party_id,
                           mailing_addr_id=addr_id,
                           delivery_addr_id=addr_id,
                           corp_num=business['business']['identifier'],
                           party_typ_cd='DIR',
                           start_event_id=event_id,
                           end_event_id=event_id if director['cessationDate'] else None,
                           appointment_dt=str(datetime.datetime.strptime(director['appointmentDate'], '%Y-%m-%d'))[:10],
                           cessation_dt=str(datetime.datetime.strptime(director['cessationDate'], '%Y-%m-%d'))[:10]
                           if director['cessationDate'] else None,
                           last_nme=director['officer']['lastName'],
                           middle_nme=director['officer']['middleInitial'],
                           first_nme=director['officer']['firstName'],
                           business_nme=business['business']['legalName'],
                           bus_company_num=business['business']['businessNumber']
                           )
        except Exception as err:
            current_app.logger.error(f'Error in director: Failed create new director for event {event_id}')
            raise err

        return corp_party_id

    @classmethod
    def _build_directors_list(cls, cursor, event_id: int = None):

        directors = cursor.fetchall()
        if not directors:
            return None

        directors_list = []
        for row in directors:
            director = Director()
            director.title = ''
            row = dict(zip([x[0].lower() for x in cursor.description], row))
            director.officer = {'firstName': row['first_nme'].strip() if row['first_nme'] else '',
                                'lastName': row['last_nme'].strip() if row['last_nme'] else '',
                                'middleInitial': row['middle_nme'] if row['middle_nme'] else ''}

            director.delivery_address = Address.get_by_address_id(row['delivery_addr_id']).as_dict()
            director.appointment_date = convert_to_json_date(row['appointment_dt']) if row['appointment_dt'] else None
            director.cessation_date = convert_to_json_date(row['cessation_dt']) if row['cessation_dt'] else None
            director.start_event_id = row['start_event_id'] if row['start_event_id'] else ''
            director.end_event_id = row['end_event_id'] if row['end_event_id'] else ''

            # this is in case the director was not ceased during this event
            if event_id and director.end_event_id and director.end_event_id > event_id:
                director.cessation_date = None

            directors_list.append(director)

        return directors_list
