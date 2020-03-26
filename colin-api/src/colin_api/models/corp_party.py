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

from colin_api.exceptions import PartiesNotFoundException
from colin_api.models import Address  # pylint: disable=cyclic-import
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date, delete_from_table_by_event_ids, stringify_list


class Party:  # pylint: disable=too-many-instance-attributes; need all these fields
    """Party object."""

    officer = None
    delivery_address = None
    mailing_address = None
    title = None
    appointment_date = None
    cessation_date = None
    start_event_id = None
    end_event_id = None
    role_type = None
    org_num = None

    roleTypes = {
        'director': 'DIR',
        'incorporator': 'INC',
        'liquidator': 'LIQ',
        'officer': 'OFF',
        'attorney': 'ATT',
        'completing party': 'COMPLETING_PARTY'
    }

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'officer': self.officer,
            'deliveryAddress': self.delivery_address,
            'mailingAddress': self.mailing_address,
            'title': self.title,
            'appointmentDate': self.appointment_date,
            'cessationDate': self.cessation_date,
            'startEventId': self.start_event_id,
            'endEventId': self.end_event_id,
            'actions': [],
            'roleType': self.role_type,
            'orgNum': self.org_num
        }

    @classmethod
    def _build_parties_list(cls, cursor, event_id: int = None):

        parties = cursor.fetchall()
        if not parties:
            return None

        party_list = []
        description = cursor.description
        for row in parties:
            party = Party()
            party.title = ''
            row = dict(zip([x[0].lower() for x in description], row))
            if row['appointment_dt']:
                party.officer = {'firstName': row['first_nme'].strip() if row['first_nme'] else '',
                                    'lastName': row['last_nme'].strip() if row['last_nme'] else '',
                                    'middleInitial': row['middle_nme'] if row['middle_nme'] else '',
                                    'organizationName': row['business_nme'] if row['business_nme'] else ''}

                party.delivery_address = Address.get_by_address_id(cursor, row['delivery_addr_id']).as_dict()
                party.mailing_address = Address.get_by_address_id(cursor, row['mailing_addr_id']).as_dict() \
                    if row['mailing_addr_id'] else party.delivery_address
                party.appointment_date =\
                    convert_to_json_date(row['appointment_dt']) if row['appointment_dt'] else None
                party.cessation_date = convert_to_json_date(row['cessation_dt']) if row['cessation_dt'] else None
                party.start_event_id = row['start_event_id'] if row['start_event_id'] else ''
                party.end_event_id = row['end_event_id'] if row['end_event_id'] else ''
                party.role_type = row['party_typ_cd'] if row['party_typ_cd'] else ''
                # this is in case the party was not ceased during this event
                if event_id and party.end_event_id and party.end_event_id > event_id:
                    party.cessation_date = None

                party_list.append(party)

        return party_list

    @classmethod
    def get_current(cls, cursor, identifier: str = None, role_type: str = 'DIR'):
        """Return current corp_parties for given identifier."""
        # Add business NME to all queries
        query = """
                select first_nme, middle_nme, last_nme, delivery_addr_id, mailing_addr_id, appointment_dt, cessation_dt,
                start_event_id, end_event_id,  business_nme, party_typ_cd
                from corp_party
                where end_event_id is NULL and corp_num=:identifier
                """
        if role_type:
            query += f" and party_typ_cd='{role_type}'"

        
        if not identifier:
            return None

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(
                query,
                identifier=identifier
            )
            parties_list = cls._build_parties_list(cursor)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting current parties info for {}'.format(identifier))
            raise err

        if not parties_list:
            raise PartiesNotFoundException(identifier=identifier)

        return parties_list

    @classmethod
    def get_by_event(cls, cursor, identifier: str = None, event_id: int = None, role_type: str = 'DIR'):
        """Get all parties active or deleted during this event."""
        query = """
                select first_nme, middle_nme, last_nme, delivery_addr_id, mailing_addr_id, appointment_dt, cessation_dt,
                start_event_id, end_event_id, business_nme, party_typ_cd
                from corp_party
                where ((start_event_id<=:event_id and end_event_id is null) or (start_event_id<=:event_id and
                cessation_dt is not null and end_event_id>=:event_id) or (start_event_id<:event_id and
                end_event_id>:event_id)) and corp_num=:identifier
                """

        if role_type:
            query += f" and party_typ_cd='{role_type}'"

        if not event_id:
            return None

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute( query,
                event_id=event_id,
                identifier=identifier
            )

            parties_list = cls._build_parties_list(cursor, event_id)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting parties info for event {}'.format(event_id))
            raise err

        if not parties_list:
            raise PartiesNotFoundException(event_id=event_id)

        return parties_list

    @classmethod
    def end_current(cls, cursor, event_id: int = None, corp_num: str = None):
        """Set all end_event_ids for current parties."""
        if not event_id:
            current_app.logger.error('Error in director: No event id given to end current parties.')

        try:
            cursor.execute("""
                update corp_party set end_event_id=:event_id where corp_num=:corp_num and end_event_id is null""",
                           event_id=event_id,
                           corp_num=corp_num
                           )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end current parties for event {event_id}')
            raise err

    @classmethod
    def end_director_by_name(cls, cursor, director: dict = None, event_id: int = None, corp_num: str = None):
        """Set all end_event_ids for given parties."""
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
                corp_num=:corp_num and upper(trim(first_nme))=upper(:first_name) and
                upper(trim(last_nme))=upper(:last_name) and (upper(trim(middle_nme))=upper(:middle_initial) or
                middle_nme is null)
                """,
                event_id=event_id,
                cessation_date=director.get('cessationDate', ''),
                corp_num=corp_num,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                middle_initial=middle_initial.strip()
            )
            if cursor.rowcount < 1:
                current_app.logger.error(f'Director name: {first_name} {middle_initial} {last_name}'
                                         f' did not match any current parties in COLIN')
                raise Exception

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end director: {director}')
            raise err

    @classmethod
    def create_new_corp_party(cls, cursor, event_id: int = None, party: dict = None, business: dict = None):
        """Insert new party into the corp_party table."""

        query = """
                insert into corp_party (corp_party_id, mailing_addr_id, delivery_addr_id, corp_num, party_typ_cd,
                start_event_id, end_event_id, appointment_dt, cessation_dt, last_nme, middle_nme, first_nme,
                bus_company_num, business_nme)
                values (:corp_party_id, :mailing_addr_id, :delivery_addr_id, :corp_num, :party_typ_cd, :start_event_id,
                :end_event_id, TO_DATE(:appointment_dt, 'YYYY-mm-dd'), TO_DATE(:cessation_dt, 'YYYY-mm-dd'), :last_nme,
                :middle_nme, :first_nme, :bus_company_num, :business_name)
                """

        completing_party_query = """
                insert into completing_party (event_id, mailing_addr_id, last_nme,
                middle_nme, first_nme)
                values (:event_id, :mailing_addr_id, :last_nme,
                :middle_nme, :first_nme)
                """

        if not event_id:
            current_app.logger.error('Error in corp_party: No event id given to create party.')
        if not party:
            current_app.logger.error('Error in corp_party: No party data given to create party.')

        # create new corp party entry
        try:
            cursor.execute("""select noncorp_party_seq.NEXTVAL from dual""")
            row = cursor.fetchone()
            corp_party_id = int(row[0])
        except Exception as err:
            current_app.logger.error('Error in corp_party: Failed to get next corp_party_id.')
            raise err
        try:
            role_type = party.get('role_type','DIR')

            delivery_info = party['deliveryAddress'] if 'deliveryAddress' in party else party['mailingAddress']
        
            # create new address
            delivery_addr_id = Address.create_new_address(cursor=cursor, address_info=delivery_info)
            mailing_addr_id = delivery_addr_id
            
            if 'mailingAddress' in party:
                mailing_addr_id = Address.create_new_address(cursor=cursor, address_info=party['mailingAddress'])
            
            
            if role_type is not 'COMPLETING_PARTY':

                cursor.execute(query,
                               corp_party_id=corp_party_id,
                               mailing_addr_id=mailing_addr_id,
                               delivery_addr_id=delivery_addr_id,
                               corp_num=business['business']['identifier'],
                               party_typ_cd=role_type,
                               start_event_id=event_id,
                               end_event_id=event_id if party.get('cessationDate','') else None,
                               appointment_dt=str(datetime.datetime.strptime(party['appointmentDate'], '%Y-%m-%d'))[:10],
                               cessation_dt=str(datetime.datetime.strptime(party['cessationDate'], '%Y-%m-%d'))[:10]
                               if party.get('cessationDate', None) else None,
                               last_nme=party['officer']['lastName'],
                               middle_nme=party['officer'].get('middleInitial', ''),
                               first_nme=party['officer']['firstName'],
                               bus_company_num=business['business'].get('businessNumber', None),
                               business_name=party['officer'].get('organizationName', ''),
                               )
            else:
                cursor.execute(completing_party_query,
                               event_id=event_id,
                               mailing_addr_id=mailing_addr_id,
                               last_nme=party['officer']['lastName'],
                               middle_nme=party['officer'].get('middleInitial', ''),
                               first_nme=party['officer']['firstName']
                               )

        except Exception as err:
            current_app.logger.error(f'Error in corp_party: Failed create new party for event {event_id}')
            raise err

        return corp_party_id

    @classmethod
    def reset_dirs_by_events(cls, cursor, event_ids: list):
        """Delete all parties created with given events and make all parties ended on given events active."""
        # get address ids of parties that will be deleted
        addrs_to_delete = Address.get_addresses_by_event(cursor=cursor, event_ids=event_ids, table='corp_party')

        # delete parties created on these events
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids, table='corp_party')

        # delete addresses associated with parties that were deleted
        Address.delete(cursor=cursor, address_ids=addrs_to_delete)

        # reset parties ended on these events
        try:
            cursor.execute(f"""
                UPDATE corp_party
                SET end_event_id = null, cessation_dt = null
                WHERE end_event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error(f'Error in corp_party: Failed to reset ended parties for events {event_ids}')
            raise err
