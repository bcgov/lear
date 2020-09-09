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

from enum import Enum

from flask import current_app

from colin_api.resources.db import DB
from colin_api.utils import get_max_value


class CorpName:
    """Corp Name object."""

    class TypeCodes(Enum):
        """Render an Enum of the CorpName Type Codes."""

        ASSUMED = 'AS'
        CORP = 'CO'
        NUMBERED_CORP = 'NB'
        TRANSLATION = 'TR'

    NAME_QUERY = (
        """
        select start_event_id, corp_nme, corp_name_typ_cd, corp_num
        from corp_name
        where corp_num=:corp_num
        """
    )

    corp_num = None
    corp_name = None
    event_id = None
    type_code = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'legalName': self.corp_name,
            'eventId': self.event_id
        }

    @classmethod
    def _create_name_objs(cls, cursor) -> list:
        """Return a CorpName obj by parsing cursor."""
        corp_names = cursor.fetchall()

        corp_name_objs = []
        for corp_name_info in corp_names:
            corp_name_info = dict(zip([x[0].lower() for x in cursor.description], corp_name_info))
            name_obj = CorpName()
            name_obj.corp_name = corp_name_info['corp_nme']
            name_obj.corp_num = corp_name_info['corp_num']
            name_obj.type_code = corp_name_info['corp_name_typ_cd']
            name_obj.event_id = corp_name_info['start_event_id']
            corp_name_objs.append(name_obj)

        return corp_name_objs

    @classmethod
    def create_corp_name(cls, cursor, corp_name_obj) -> CorpName:
        """Add record to the CORP NAME table on incorporation."""
        try:
            search_name = cursor.callfunc('get_search_name', str, [corp_name_obj.corp_name])
            max_sequence_num = get_max_value(
                cursor=cursor,
                corp_num=corp_name_obj.corp_num,
                table='corp_name',
                column='corp_name_seq_num'
            )
            cursor.execute(
                """
                insert into CORP_NAME (CORP_NAME_TYP_CD, CORP_NAME_SEQ_NUM, DD_CORP_NUM, END_EVENT_ID, CORP_NME,
                    CORP_NUM, START_EVENT_ID, SRCH_NME)
                values (:type_code, :sequence_num, NULL, NULL, :corp_name, :corp_num, :event_id, :search_name)
                """,
                type_code=corp_name_obj.type_code,
                sequence_num=max_sequence_num + 1 if max_sequence_num else 0,
                corp_name=corp_name_obj.corp_name,
                corp_num=corp_name_obj.corp_num,
                event_id=corp_name_obj.event_id,
                search_name=search_name
            )

        except Exception as err:
            current_app.logger.error(f'Error inserting corp name {corp_name_obj.corp_name}.')
            raise err

    @classmethod
    def create_translations(cls, cursor, corp_num, event_id, translations):
        """Add records to the CORP NAME table for corp name translations."""
        try:
            curr_corp_name = ''
            max_sequence_num = get_max_value(
                cursor=cursor,
                corp_num=corp_num,
                table='corp_name',
                column='corp_name_seq_num'
            )
            sequence_number = max_sequence_num + 1 if max_sequence_num else 0
            for name in translations:
                curr_corp_name = name
                search_name = cursor.callfunc('get_search_name', str, [name])
                cursor.execute(
                    """
                    insert into CORP_NAME (CORP_NAME_TYP_CD, CORP_NAME_SEQ_NUM, DD_CORP_NUM, END_EVENT_ID, CORP_NME,
                        CORP_NUM, START_EVENT_ID, SRCH_NME)
                    values (:type_code, :sequence_num, NULL, NULL, :corp_name, :corp_num, :event_id, :search_name)
                    """,
                    type_code=CorpName.TypeCodes.TRANSLATION.value,
                    sequence_num=sequence_number,
                    corp_name=name,
                    corp_num=corp_num,
                    event_id=event_id,
                    search_name=search_name
                )
                sequence_number = sequence_number + 1

        except Exception as err:
            current_app.logger.error(f'Error inserting corp name {curr_corp_name}.')
            raise err

    @classmethod
    def end_current(cls, cursor, event_id: str, corp_num: str):
        """End current entity name/s."""
        try:
            cursor.execute(
                """
                update corp_name
                set end_event_id=:event_id
                where corp_num=:corp_num and corp_name_typ_cd in ('CO','NB') and end_event_id is null
                """,
                event_id=event_id,
                corp_num=corp_num
            )

        except Exception as err:
            current_app.logger.error(f'error ending current corp names for corp: {corp_num}')
            raise err

    @classmethod
    def end_translation(cls, cursor, event_id: str, corp_num: str, corp_name: str):
        """End specific tranlsation type name."""
        try:
            cursor.execute(
                """
                update corp_name
                set end_event_id=:event_id
                where corp_num=:corp_num and corp_name_typ_cd='TR' and end_event_id is null and corp_nme=:corp_name
                """,
                event_id=event_id,
                corp_name=corp_name,
                corp_num=corp_num
            )

        except Exception as err:
            current_app.logger.error(f'error ending translation {corp_name} for {corp_num}')
            raise err

    @classmethod
    def get_by_event(cls, cursor, corp_num: str = None, event_id: str = None) -> CorpName:
        """Get the entity name corresponding with the given event id."""
        if not corp_num or not event_id:
            return None
        try:
            if not cursor:
                cursor = DB.connection.cursor()
            querystring = cls.NAME_QUERY + ' and start_event_id=:event_id'
            cursor.execute(querystring, corp_num=corp_num, event_id=event_id)

            return (cls._create_name_objs(cursor=cursor))[0]

        except Exception as err:
            current_app.logger.error(f'error getting corp name for {corp_num} by event {event_id}')
            raise err

    @classmethod
    def get_current(cls, cursor, corp_num: str) -> list:
        """Get current entity names."""
        try:
            querystring = cls.NAME_QUERY + ' and end_event_id is null'
            cursor.execute(querystring, corp_num=corp_num)

            return cls._create_name_objs(cursor=cursor)

        except Exception as err:
            current_app.logger.error(f'error getting current corp names for {corp_num}')
            raise err

    @classmethod
    def get_current_by_type(cls, cursor, corp_num: str, type_code: str) -> list:
        """Get current entity names by type code."""
        try:
            querystring = cls.NAME_QUERY + ' and corp_name_typ_cd=:type_code and end_event_id is null'
            cursor.execute(querystring, corp_num=corp_num, type_code=type_code)
            return cls._create_name_objs(cursor=cursor)

        except Exception as err:
            current_app.logger.error(f'error getting current corp names by type {type_code} for {corp_num}')
            raise err
