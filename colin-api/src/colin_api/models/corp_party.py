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
    role_desc = None
    appointment_date = None
    cessation_date = None
    start_event_id = None
    end_event_id = None
    corp_party_id = None
    prev_party_id = None
    corp_num = None
    offices_held = None

    role_types = {
        'Applicant': 'APP',
        'Attorney': 'ATT',
        'Completing Party': 'CPRTY',
        'Custodian': 'RCC',
        'Director': 'DIR',
        'Firm Business Owner': 'FBO',
        'Firm Individual Owner': 'FIO',
        'Incorporator': 'INC',
        'Liquidator': 'LIQ',
        'Officer': 'OFF',
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
            'roles': self.roles,
            'id': self.corp_party_id
        }

    def get_start_event_date(self, cursor):
        """Get the start event date of the party."""
        query = """
                SELECT event_typ_cd, event_timestmp, effective_dt
                FROM event e
                  LEFT JOIN filing f on f.event_id = e.event_id
                WHERE e.event_id=:event_id
                """
        dates = cursor.execute(query, event_id=self.start_event_id).fetchone()
        description = cursor.description
        dates = dict(zip([x[0].lower() for x in description], dates))
        if dates['event_typ_cd'] in ['CONVICORP', 'CONVAMAL', 'CONVCIN']:
            return None
        return convert_to_json_date(dates['effective_dt'] or dates['event_timestmp'])

    @classmethod
    def _parse_officer(cls, row):
        officer_obj = {
            'firstName': (row.get('first_nme', '') or '').strip(),
            'lastName': (row.get('last_nme', '') or '').strip(),
            'middleInitial': (row.get('middle_nme', '') or '').strip(),
            'organizationName': (row.get('business_nme', '') or '').strip()
        }
        if officer_obj['organizationName']:
            officer_obj['partyType'] = 'organization'
        else:
            officer_obj['partyType'] = 'person'
        return officer_obj

    @classmethod
    def _get_offices_held(cls, cursor, corp_party_id: str) -> List[Dict]:
        """Get the offices held by the party."""
        query = """
                SELECT officer_typ_cd
                FROM offices_held
                WHERE corp_party_id=:corp_party_id
                """
        cursor.execute(query, corp_party_id=corp_party_id)
        offices = cursor.fetchall()

        return [row[0] for row in offices]

    @classmethod
    def _parse_party(cls, cursor, row: dict) -> Party:
        """Parse the party row."""
        party = Party()
        party.title = ''
        party.officer = Party._parse_officer(row)
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
        party.role_desc = (row.get('short_desc', '')) or ''
        party.corp_party_id = row.get('corp_party_id', None)
        party.prev_party_id = row.get('prev_party_id', None)
        party.corp_num = row.get('corp_num', None)

        if party.role_type == cls.role_types['Officer']:
            party.offices_held = cls._get_offices_held(cursor, party.corp_party_id)
        return party

    @classmethod
    def _build_parties_list(cls, cursor, corp_num: str, event_id: int = None) -> Optional[List[Party]]:
        """Return the party list from the query."""
        parties = cursor.fetchall()

        if not parties:
            return None

        completing_parties = {}
        party_list = []
        description = cursor.description
        for row in parties:
            row = dict(zip([x[0].lower() for x in description], row))
            party = Party._parse_party(cursor, row)

            if not party.appointment_date:
                party.appointment_date = Business.get_founding_date(cursor=cursor, corp_num=corp_num)

            if party.role_type == cls.role_types['Director'] and not party.delivery_address:
                current_app.logger.error('Bad director data for party id: %s, corp num: %s',
                                         party.corp_party_id,
                                         party.corp_num)

            party_list.append(party)

        if event_id:
            completing_parties = cls.get_completing_parties(cursor, event_id)
        return cls.group_parties(party_list, completing_parties)

    @classmethod
    def group_parties(cls, parties: List['Party'], completing_parties: dict) -> List[Party]:
        """Group parties based on roles for LEAR formatting."""
        role_dict = {v: k for k, v in cls.role_types.items()}  # Used as a lookup for role names

        grouped_list = []
        role_func = (lambda x:  # pylint: disable=unnecessary-lambda-assignment; # noqa: E731;
                     x.officer['firstName'] +
                     x.officer['middleInitial'] +
                     x.officer['lastName'] +
                     x.officer['organizationName'])

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
    def get_all_parties(cls, cursor, corp_num: str) -> List[Party]:
        """Return all corp_parties for the given corp_num."""
        query = """
                SELECT first_nme, middle_nme, last_nme, delivery_addr_id, mailing_addr_id,
                  appointment_dt, cessation_dt, start_event_id, end_event_id, business_nme,
                  cp.party_typ_cd, corp_party_id, prev_party_id, corp_num, pt.short_desc
                FROM corp_party cp
                  JOIN party_type pt on pt.party_typ_cd = cp.party_typ_cd
                WHERE corp_num=:identifier
                ORDER BY start_event_id asc
                """
        party_list = []
        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(query, identifier=corp_num)
            description = cursor.description

            parties = cursor.fetchall()
            if not parties:
                raise PartiesNotFoundException(identifier=corp_num)

            party_id_map: Dict[str, Party] = {}
            child_party_ids: List[str] = []
            # NB: list is already ordered by start_event_id so we can assume the
            #     1st record is the oldest child and the last one is the newest parent
            for party_row in parties:
                party_row = dict(zip([x[0].lower() for x in description], party_row))
                party = Party._parse_party(cursor, party_row)
                party_id_map[party.corp_party_id] = party
                if party.prev_party_id:
                    # only need previous party information for appointment date when applicable
                    if not party.appointment_date and party_id_map.get(party.prev_party_id):
                        # set the appointment date from previous party record
                        child_party = party_id_map[party.prev_party_id]
                        party.appointment_date = child_party.appointment_date or \
                            child_party.get_start_event_date(cursor) or 'unknown'
                    # mark the prev_party_id as a child so its not returned
                    # (not removed in case another party record references it)
                    child_party_ids.append(party.prev_party_id)
                if not party.appointment_date:
                    # wasn't set by a previous record so set it by its event or filing date
                    party.appointment_date = party.get_start_event_date(cursor)

            # only return the top level parent records
            for party_id in party_id_map:  # pylint: disable=consider-using-dict-items
                if party_id not in child_party_ids:
                    party = party_id_map[party_id]
                    if party.appointment_date == 'unknown':
                        # marked as unknown previously to prevent parent record
                        # overwriting a child None value with the parent event timestamp
                        party.appointment_date = None

                    party.roles = [{
                        'appointmentDate': party.appointment_date,
                        'cessationDate': party.cessation_date,
                        'roleType': party.role_desc}]

                    party_list.append(party)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.debug(err.with_traceback(None))
            current_app.logger.error('Error in get_all_parties for %s', corp_num)
            raise err

        if not party_list:
            raise PartiesNotFoundException(identifier=corp_num)

        return party_list

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

        if not parties_list and role_type != 'Officer':
            raise PartiesNotFoundException(identifier=corp_num)

        return parties_list

    @classmethod
    def end_current(cls, cursor, event_id: int, corp_num: str, role_type: str = None):
        """Set all end_event_ids for current parties."""
        try:
            query = """update corp_party
                    set end_event_id=:event_id
                    where corp_num=:corp_num and end_event_id is null
                    """
            if role_type:
                query += f" and party_typ_cd='{Party.role_types[role_type]}'"

            cursor.execute(
                query,
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
            where party_typ_cd='DIR' and end_event_id is null and corp_num=:corp_num
            """
        )
        try:
            officer = director['officer']
            if officer.get('organizationName'):
                query = query + ' and upper(trim(business_nme))=upper(:business_name)'
                cursor.execute(
                    query,
                    event_id=event_id,
                    cessation_date=director.get('cessationDate', ''),
                    corp_num=corp_num,
                    business_name=officer['organizationName']
                )
            else:
                query = query + \
                    """
                    and upper(trim(first_nme))=upper(:first_name) and upper(trim(last_nme))=upper(:last_name)
                    and (upper(trim(middle_nme))=upper(:middle_initial) or middle_nme is null)
                    """
                first_name = officer.get('prevFirstName') or officer.get('firstName')
                last_name = officer.get('prevLastName') or officer.get('lastName')
                middle_initial = (officer.get('prevMiddleInitial') or
                                  officer.get('middleInitial') or
                                  officer.get('middleName'))

                cursor.execute(
                    query,
                    event_id=event_id,
                    cessation_date=director.get('cessationDate', ''),
                    corp_num=corp_num,
                    first_name=(first_name or '').strip(),
                    last_name=(last_name or '').strip(),
                    middle_initial=(middle_initial or '').strip()
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
              bus_company_num, business_nme, office_notification_dt, prev_party_id)
            values (:corp_party_id, :mailing_addr_id, :delivery_addr_id, :corp_num, :party_typ_cd, :start_event_id,
              :end_event_id, TO_DATE(:appointment_dt, 'YYYY-mm-dd'), TO_DATE(:cessation_dt, 'YYYY-mm-dd'),
              :last_nme, :middle_nme, :first_nme, :bus_company_num, :business_name,
              TO_DATE(:office_notification_dt, 'YYYY-mm-dd'), :prev_party_id)
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
                        last_nme=party['officer'].get('lastName', ''),
                        middle_nme=(party['officer'].get('middleInitial') or
                                    party['officer'].get('middleName')) or '',
                        first_nme=party['officer'].get('firstName', ''),
                        email=party['officer'].get('email', '')
                    )
                else:
                    cursor.execute(
                        completing_party_query,
                        event_id=event_id,
                        mailing_addr_id=mailing_addr_id,
                        last_nme=party['officer'].get('lastName', ''),
                        middle_nme=(party['officer'].get('middleInitial') or
                                    party['officer'].get('middleName')) or '',
                        first_nme=party['officer'].get('firstName', ''),
                        email=party['officer'].get('email', '')
                    )
            else:
                date_format = '%Y-%m-%d'
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
                            """, new_num=corp_party_id + 1)

                except Exception as err:
                    current_app.logger.error('Error in corp_party: Failed to get next corp_party_id.')
                    raise err
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
                        appointment_dt=(
                            str(datetime.datetime.strptime(party['appointmentDate'], date_format))[:10]
                            if party.get('appointmentDate', None) else None),
                        cessation_dt=(
                            str(datetime.datetime.strptime(party['cessationDate'], date_format))[:10]
                            if party.get('cessationDate', None) else None),
                        office_notification_dt=(
                            str(datetime.datetime.strptime(party['officeNotificationDt'], date_format))[:10]
                            if party.get('officeNotificationDt') else None),
                        last_nme=party['officer'].get('lastName', ''),
                        middle_nme=(party['officer'].get('middleInitial') or
                                    party['officer'].get('middleName')) or '',
                        first_nme=party['officer'].get('firstName', ''),
                        bus_company_num=None,
                        business_name=party['officer'].get('organizationName', ''),
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
                        appointment_dt=(
                            str(datetime.datetime.strptime(party['appointmentDate'], date_format))[:10]
                            if party.get('appointmentDate', None) else None),
                        cessation_dt=(
                            str(datetime.datetime.strptime(party['cessationDate'], date_format))[:10]
                            if party.get('cessationDate', None) else None),
                        office_notification_dt=(
                            str(datetime.datetime.strptime(party['officeNotificationDt'], date_format))[:10]
                            if party.get('officeNotificationDt') else None),
                        last_nme=party['officer'].get('lastName', ''),
                        middle_nme=(party['officer'].get('middleInitial') or
                                    party['officer'].get('middleName')) or '',
                        first_nme=party['officer'].get('firstName', ''),
                        bus_company_num=None,
                        business_name=party['officer'].get('organizationName', '')
                    )

        except Exception as err:
            current_app.logger.error(f'Error in corp_party: Failed create new party for {corp_num}')
            raise err

    @classmethod
    def compare_parties(cls, party: Party, officer_json: Dict):
        """Compare corp party with json, return true if their names are equal."""
        if (officer_json.get('prevFirstName') or
            officer_json.get('prevLastName') or
                officer_json.get('prevOrganizationName')):
            first_name = (officer_json.get('prevFirstName') or '')
            middle_name = (officer_json.get('prevMiddleInitial') or '')
            last_name = (officer_json.get('prevLastName') or '')
            org_name = (officer_json.get('prevOrganizationName') or '')
        else:
            first_name = (officer_json.get('firstName') or '')
            middle_name = (officer_json.get('middleInitial') or '')
            last_name = (officer_json.get('lastName') or '')
            org_name = (officer_json.get('organizationName') or '')
        if ((party.officer.get('firstName') or '').strip().upper() == first_name.strip().upper() and
                (party.officer.get('middleInitial') or '').strip().upper() == middle_name.strip().upper() and
                (party.officer.get('lastName') or '').strip().upper() == last_name.strip().upper() and
                (party.officer.get('organizationName') or '').strip().upper() == org_name.strip().upper()):
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
