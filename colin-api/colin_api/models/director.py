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
from flask import current_app
from colin_api.utils import convert_to_json_date
from colin_api.exceptions import DirectorsNotFoundException
from colin_api.models import Address
from colin_api.resources.db import db


class Director:

    officer = None
    delivery_address = None
    # mailing_address = None
    title = None
    appointment_date = None
    cessation_date = None
    start_event_id = None

    def as_dict(self):
        return {
            'officer': self.officer,
            'deliveryAddress': self.delivery_address,
            # 'mailingAddress': self.mailing_address,
            'title': self.title
        }

    @classmethod
    def get_current(cls, identifier: str = None):

        if not identifier:
            return None

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                """
                select first_nme, middle_nme, last_nme, delivery_addr_id, appointment_dt, cessation_dt, start_event_id
                from corp_party
                where end_event_id is NULL and corp_party.corp_num=:identifier and corp_party.party_typ_cd='DIR'
                """,
                identifier=identifier
            )
            directors_list = cls._build_directors_list(cursor)

        except Exception as err:
            current_app.logger.error('error getting directors info for {}'.format(identifier))
            raise err

        if not directors_list:
            raise DirectorsNotFoundException(identifier=identifier)

        return directors_list

    @classmethod
    def get_by_event(cls, event_id: str = None):
        """gets all directors added/deleted during this event"""
        if not event_id:
            return None

        try:
            cursor = db.connection.cursor()
            cursor.execute(
                """
                select first_nme, middle_nme, last_nme, delivery_addr_id, appointment_dt, cessation_dt, start_event_id
                from corp_party
                where (start_event_id=:event_id or end_event_id=:event_id) and party_typ_cd='DIR'
                """,
                event_id=event_id
            )
            directors_list = cls._build_directors_list(cursor)

        except Exception as err:
            current_app.logger.error('error getting directors info for event {}'.format(event_id))
            raise err

        if not directors_list:
            raise DirectorsNotFoundException()

        return directors_list

    @classmethod
    def _build_directors_list(cls, cursor):

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
            director.appointment_date = row['appointment_dt']
            director.cessation_date = row['cessation_dt']
            director.start_event_id = row['start_event_id']

            directors_list.append(director)

        return directors_list
