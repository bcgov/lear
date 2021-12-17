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
from __future__ import annotations

import datetime
import itertools
from typing import Dict, List, Optional

from flask import current_app

from colin_api.exceptions import PartiesNotFoundException
from colin_api.models import Address, Business  # pylint: disable=cyclic-import
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date, delete_from_table_by_event_ids, stringify_list


class Party:  # pylint: disable=too-many-instance-attributes; need all these fields
    """Party object."""

    # for party (i.e. person that might have multiple roles)
    officer = None
    delivery_address = None
    mailing_address = None
    title = None
    roles = None
    # for role (i.e. director)
    role_type = None
    appointment_date = None
    cessation_date = None
    start_event_id = None
    end_event_id = None
    corp_party_id = None

    role_types = {
        'Director': 'DIR',
        'Incorporator': 'INC',
        'Liquidator': 'LIQ',
        'Officer': 'OFF',
        'Attorney': 'ATT',
        'Completing Party': 'CPRTY',
        'Custodian': 'RCC'
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
            'roles': self.roles
        }

    @classmethod
    def _get_officer(cls, row):
        officer_obj = {
            'firstName': (row.get('first_nme', '') or '').strip(),
            'lastName': (row.get('last_nme', '') or '').strip(),
            'middleInitial': (row.get('middle_nme', '') or '').strip(),
            'orgName': (row.get('business_nme', '') or '').strip()
        }
        return officer_obj

    @classmethod
    def _build_parties_list(cls, cursor, corp_num: str, event_id: int = None) -> Optional[List]:
        parties = cursor.fetchall()

        if not parties:
            return None

        completing_parties = {}
        party_list = []
        description = cursor.description
        for row in parties:
            party = Party()
            party.title = ''
            row = dict(zip([x[0].lower() for x in description], row))
            if not row['appointment_dt']:
                row['appointment_dt'] = Business.get_founding_date(cursor=cursor, corp_num=corp_num)
            party.officer = cls._get_officer(row)
            if (row.get('party_typ_cd', None) == cls.role_types['Director']) and not row['delivery_addr_id']:
                current_app.logger.error(
                    f"Bad director data for {party.officer.get('firstName')} {party.officer.get('lastName')} {corp_num}"
                )
            else:
                if row['delivery_addr_id']:
                    party.delivery_address = Address.get_by_address_id(cursor, row['delivery_addr_id']).as_dict()
                party.mailing_address = Address.get_by_address_id(cursor, row['mailing_addr_id']).as_dict() \
                    if row['mailing_addr_id'] else party.delivery_address
                party.appointment_date =\
                    convert_to_json_date(row.get('appointment_dt', None))
                party.cessation_date = convert_to_json_date(row.get('cessation_dt', None))
                party.start_event_id = (row.get('start_event_id', '')) or ''
                party.end_event_id = (row.get('end_event_id', '')) or ''
                party.role_type = (row.get('party_typ_cd', '')) or ''
                party.corp_party_id = row.get('corp_party_id', None)

                party_list.append(party)
        if event_id:
            completing_parties = cls.get_completing_parties(cursor, event_id)
        return cls.group_parties(party_list, completing_parties)

    @classmethod
    def group_parties(cls, parties: List['Party'], completing_parties: dict) -> List:
        """Group parties based on roles for LEAR formatting."""
        role_dict = {v: k for k, v in cls.role_types.items()}  # Used as a lookup for role names

        grouped_list = []
        role_func = (lambda x: x.officer['firstName'] + x.officer['middleInitial'] + x.officer['lastName']
                     + x.officer['orgName'])  # noqa: E731;

        # CORP_PARTIES are stored as a separate row per Role, and need to be grouped to return a list of
        # Role(s) within each Party object. First the rows are grouped in-memory by party/organization name
        # (dictionary of parties)
        parties_dict = {k: list(v) for k, v in itertools.groupby(parties, key=role_func)}

        # Iterate over each grouping, the first value represents the Party. All rows
        # are then iterated to construct the Roles array
        for party_name, party_roles in parties_dict.items():  # pylint: disable=unused-variable;
            party = party_roles[0]  # The party
            roles = []
            # Fetch the role from each element in the Party array
            if party_name in completing_parties.keys():
                roles.append(completing_parties[party_name])

            for i in party_roles:
                role = i.role_type
                roles.append(
                    {
                        'roleType': role_dict[role],
                        'appointmentDate': i.appointment_date,
                        'cessationDate': i.cessation_date
                    }
                )
            party.roles = roles
            grouped_list.append(party)
        return grouped_list

    @classmethod
    def get_completing_parties(cls, cursor, event_id: int) -> Dict:
        """Retrieve the completing parties for an event."""
        query = f"""
                select first_nme, middle_nme, last_nme, corp.recognition_dts from
                completing_party cp join event e on cp.event_id = e.event_id
                join corporation corp on e.corp_num = corp.corp_num
                where cp.event_id = {event_id}
                """

        cursor.execute(query)
        parties = cursor.fetchall()
        completing_parties = {}
        description = cursor.description

        for row in parties:
            row = dict(zip([x[0].lower() for x in description], row))
            party_name = (
                row.get('first_nme', '') or '' +
                row.get('middle_nme', '') or '' +
                row.get('last_nme', '') or ''
            )

            appointed = row['recognition_dts']
            completing_parties[party_name] = {
                'roleType': 'Completing Party',
                'appointmentDate': appointed
            }

        return completing_parties

    @classmethod
    def get_current(cls, cursor, corp_num: str, role_type: str = 'Director') -> List:
        """Return current corp_parties for given identifier."""
        query = """
                select first_nme, middle_nme, last_nme, delivery_addr_id, mailing_addr_id, appointment_dt, cessation_dt,
                start_event_id, end_event_id,  business_nme, party_typ_cd, corp_party_id
                from corp_party
                where end_event_id is NULL and corp_num=:identifier
                """
        if role_type:
            query += f" and party_typ_cd='{Party.role_types[role_type]}'"

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(
                query,
                identifier=corp_num
            )
            parties_list = cls._build_parties_list(cursor, corp_num)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'error getting current parties info for {corp_num}')
            raise err

        if not parties_list:
            raise PartiesNotFoundException(identifier=corp_num)

        return parties_list

    @classmethod
    def get_by_event(cls, cursor, corp_num: str, event_id: int, role_type: str = 'Director') -> List:
        """Get all parties active or deleted during this event."""
        query = """
                select first_nme, middle_nme, last_nme, delivery_addr_id, mailing_addr_id,
                       appointment_dt, cessation_dt, start_event_id, end_event_id,
                       business_nme, party_typ_cd, corp_party_id
                from corp_party
                where corp_num=:corp_num
                  and (start_event_id = :event_id
                        or (start_event_id<:event_id and end_event_id is null)
                        or (start_event_id<:event_id and cessation_dt is not null and end_event_id>=:event_id)
                        or (start_event_id<:event_id and end_event_id>:event_id))
                """

        if role_type:
            query += f" and party_typ_cd='{Party.role_types[role_type]}'"

        try:
            cursor.execute(
                query,
                event_id=event_id,
                corp_num=corp_num
            )

            parties_list = cls._build_parties_list(cursor, corp_num, event_id)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'error getting parties info for {corp_num}')
            raise err

        if not parties_list:
            raise PartiesNotFoundException(identifier=corp_num)

        return parties_list

    @classmethod
    def end_current(cls, cursor, event_id: int, corp_num: str):
        """Set all end_event_ids for current parties."""
        try:
            cursor.execute(
                """
                update corp_party
                set end_event_id=:event_id
                where corp_num=:corp_num and end_event_id is null
                """,
                event_id=event_id,
                corp_num=corp_num
            )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end current parties for {corp_num}')
            raise err

    @classmethod
    def end_director_by_name(cls, cursor, director: Dict, event_id: int, corp_num: str):
        """Set all end_event_ids for given parties."""
        query = (
            """
            update corp_party
            set end_event_id=:event_id, cessation_dt=TO_DATE(:cessation_date, 'YYYY-mm-dd')
            where corp_num=:corp_num
            """
        )
        try:
            officer = director['officer']
            if officer.get('orgName'):
                query = query + ' and upper(trim(business_nme))=upper(:business_name)'
                cursor.execute(
                    query,
                    event_id=event_id,
                    cessation_date=director.get('cessationDate', ''),
                    corp_num=corp_num,
                    business_name=officer['orgName']
                )
            else:
                query = query + \
                    """
                    and upper(trim(first_nme))=upper(:first_name) and upper(trim(last_nme))=upper(:last_name)
                    and (upper(trim(middle_nme))=upper(:middle_initial) or middle_nme is null)
                    """
                first_name = officer.get('prevFirstName') or officer['firstName']
                last_name = officer.get('prevLastName') or officer['lastName']
                middle_initial = officer.get('prevMiddleInitial', '') or officer.get('middleInitial', '')

                cursor.execute(
                    query,
                    event_id=event_id,
                    cessation_date=director.get('cessationDate', ''),
                    corp_num=corp_num,
                    first_name=first_name.strip(),
                    last_name=last_name.strip(),
                    middle_initial=middle_initial.strip()
                )
            if cursor.rowcount < 1:
                current_app.logger.error(f'Could not find director {officer}')
                raise PartiesNotFoundException(identifier=corp_num)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'Error in director: Failed to end director: {director}')
            raise err

    @classmethod
    # pylint: disable=too-many-locals; one extra
    def create_new_corp_party(cls, cursor, event_id: int, party: Dict, business: Dict):
        """Insert new party into the corp_party table."""
        query = \
            """
            insert into corp_party (corp_party_id, mailing_addr_id, delivery_addr_id, corp_num, party_typ_cd,
              start_event_id, end_event_id, appointment_dt, cessation_dt, last_nme, middle_nme, first_nme,
              bus_company_num, business_nme, prev_party_id)
            values (:corp_party_id, :mailing_addr_id, :delivery_addr_id, :corp_num, :party_typ_cd, :start_event_id,
              :end_event_id, TO_DATE(:appointment_dt, 'YYYY-mm-dd'), TO_DATE(:cessation_dt, 'YYYY-mm-dd'),
              :last_nme, :middle_nme, :first_nme, :bus_company_num, :business_name, :prev_party_id)
            """

        completing_party_query = \
            """
            insert into completing_party (event_id, mailing_addr_id, last_nme, middle_nme, first_nme,
              email_req_address)
            values (:event_id, :mailing_addr_id, :last_nme, :middle_nme, :first_nme, :email)
            """
        completing_party_update_query = \
            """
            update completing_party
            set mailing_addr_id=:mailing_addr_id, last_nme=:last_nme, middle_nme=:middle_nme, first_nme=:first_nme,
              email_req_address=:email
            where event_id=:event_id
            """

        # create new corp party entry
        corp_num = business['business']['identifier']
        try:
            if corp_num == 'CP':
                cursor.execute("""select noncorp_party_seq.NEXTVAL from dual""")
                row = cursor.fetchone()
                corp_party_id = int(row[0])
            else:
                cursor.execute("""
                    SELECT id_num
                    FROM system_id
                    WHERE id_typ_cd = 'CP'
                    FOR UPDATE
                """)

                corp_party_id = int(cursor.fetchone()[0])

                if corp_party_id:
                    cursor.execute("""
                        UPDATE system_id
                        SET id_num = :new_num
                        WHERE id_typ_cd = 'CP'
                    """, new_num=corp_party_id+1)

        except Exception as err:
            current_app.logger.error('Error in corp_party: Failed to get next corp_party_id.')
            raise err
        try:
            role_type = party.get('role_type', 'DIR')

            delivery_info = party['deliveryAddress'] if 'deliveryAddress' in party else party['mailingAddress']
            # create new address
            delivery_addr_id = Address.create_new_address(cursor=cursor, address_info=delivery_info, corp_num=corp_num)
            mailing_addr_id = delivery_addr_id

            if 'mailingAddress' in party:
                mailing_addr_id = Address.create_new_address(
                    cursor=cursor, address_info=party['mailingAddress'], corp_num=corp_num)
            if role_type == 'CPRTY':
                if party.get('prev_event_id'):
                    # update old completing party entry instead of creating a new one
                    cursor.execute(
                        completing_party_update_query,
                        event_id=party['prev_event_id'],
                        mailing_addr_id=mailing_addr_id,
                        last_nme=party['officer']['lastName'],
                        middle_nme=party['officer'].get('middleInitial', ''),
                        first_nme=party['officer']['firstName'],
                        email=party['officer']['email']
                    )
                else:
                    cursor.execute(
                        completing_party_query,
                        event_id=event_id,
                        mailing_addr_id=mailing_addr_id,
                        last_nme=party['officer']['lastName'],
                        middle_nme=party['officer'].get('middleInitial', ''),
                        first_nme=party['officer']['firstName'],
                        email=party['officer']['email']
                    )
            else:
                date_format = '%Y-%m-%d'
                if party.get('prev_id'):
                    cursor.execute(
                        query,
                        corp_party_id=corp_party_id,
                        mailing_addr_id=mailing_addr_id,
                        delivery_addr_id=delivery_addr_id,
                        corp_num=corp_num,
                        party_typ_cd=role_type,
                        start_event_id=event_id,
                        end_event_id=event_id if party.get('cessationDate', '') else None,
                        appointment_dt=str(datetime.datetime.strptime(party['appointmentDate'], date_format))[:10],
                        cessation_dt=str(datetime.datetime.strptime(party['cessationDate'], date_format))[:10]
                        if party.get('cessationDate', None) else None,
                        last_nme=party['officer']['lastName'],
                        middle_nme=party['officer'].get('middleInitial', ''),
                        first_nme=party['officer']['firstName'],
                        bus_company_num=business['business'].get('businessNumber', None),
                        business_name=party['officer'].get('orgName', ''),
                        prev_party_id=party['prev_id']
                    )
                else:
                    query = query.replace(', prev_party_id', '').replace(', :prev_party_id', '')
                    cursor.execute(
                        query,
                        corp_party_id=corp_party_id,
                        mailing_addr_id=mailing_addr_id,
                        delivery_addr_id=delivery_addr_id,
                        corp_num=corp_num,
                        party_typ_cd=role_type,
                        start_event_id=event_id,
                        end_event_id=event_id if party.get('cessationDate', '') else None,
                        appointment_dt=str(datetime.datetime.strptime(party['appointmentDate'], date_format))[:10],
                        cessation_dt=str(datetime.datetime.strptime(party['cessationDate'], date_format))[:10]
                        if party.get('cessationDate', None) else None,
                        last_nme=party['officer']['lastName'],
                        middle_nme=party['officer'].get('middleInitial', ''),
                        first_nme=party['officer']['firstName'],
                        bus_company_num=business['business'].get('businessNumber', None),
                        business_name=party['officer'].get('orgName', '')
                    )

        except Exception as err:
            current_app.logger.error(f'Error in corp_party: Failed create new party for {corp_num}')
            raise err

        return corp_party_id

    @classmethod
    def compare_parties(cls, party: Party, officer_json: Dict):
        """Compare corp party with json, return true if their names are equal."""
        if officer_json.get('prevFirstName') or officer_json.get('prevLastName') or officer_json.get('prevOrgName'):
            first_name = officer_json.get('prevFirstName', '')
            middle_name = officer_json.get('prevMiddleInitial', '')
            last_name = officer_json.get('prevLastName', '')
            org_name = officer_json.get('prevOrgName', '')
        else:
            first_name = officer_json.get('firstName', '')
            middle_name = officer_json.get('middleInitial', '')
            last_name = officer_json.get('lastName', '')
            org_name = officer_json.get('orgName', '')
        if party.officer.get('firstName', '').strip().upper() == first_name.strip().upper() \
                and party.officer.get('middleInitial', '').strip().upper() == middle_name.strip().upper() \
                and party.officer.get('lastName', '').strip().upper() == last_name.strip().upper() \
                and party.officer.get('orgName', '').strip().upper() == org_name.strip().upper():
            return True
        return False

    @classmethod
    def reset_dirs_by_events(cls, cursor, event_ids: List):
        """Delete all parties created with given events and make all parties ended on given events active."""
        # get address ids of parties that will be deleted
        addrs_to_delete = Address.get_addresses_by_event(cursor=cursor, event_ids=event_ids, table='corp_party')

        # delete parties created on these events
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids, table='corp_party')

        # delete parties created on these events
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids, table='completing_party', column='event_id')

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
