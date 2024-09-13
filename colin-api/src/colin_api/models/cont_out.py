# Copyright © 2024 Province of British Columbia
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
"""This module holds data about cont_out table."""
from __future__ import annotations

from typing import List

from flask import current_app

from colin_api.resources.db import DB


class ContOut:
    """ContOut object."""

    corp_num = None
    start_event_id = None
    can_jur_typ_cd = None
    cont_out_dt = None
    othr_juri_desc = None
    home_company_nme = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'corpNum': self.corp_num,
            'startEventId': self.start_event_id,
            'canJurTypCd': self.can_jur_typ_cd,
            'contOutDt': self.cont_out_dt,
            'othrJuriDesc': self.othr_juri_desc,
            'homeCompanyNme': self.home_company_nme,
        }

    @classmethod
    def _create_cont_out_objs(cls, cursor) -> List:
        """Return a cont_out obj by parsing cursor."""
        cont_outs = cursor.fetchall()

        cont_out_objs = []
        for cont_out in cont_outs:
            cont_out = dict(zip([x[0].lower() for x in cursor.description], cont_out))
            cont_out_obj = ContOut()
            cont_out_obj.corp_num = cont_out['corp_num']
            cont_out_obj.start_event_id = cont_out['start_event_id']
            cont_out_obj.can_jur_typ_cd = cont_out['can_jur_typ_cd']
            cont_out_obj.cont_out_dt = cont_out['cont_out_dt']
            cont_out_obj.othr_juri_desc = cont_out['othr_juri_desc']
            cont_out_obj.home_company_nme = cont_out['home_company_nme']
            cont_out_objs.append(cont_out_obj)

        return cont_out_objs

    @classmethod
    def create_cont_out(cls, cursor, cont_out_obj) -> ContOut:
        """Add record to the cont_out table."""
        try:
            cursor.execute(
                """
                insert into cont_out
                    (CORP_NUM, START_EVENT_ID, CAN_JUR_TYP_CD, CONT_OUT_DT, OTHR_JURI_DESC, HOME_COMPANY_NME)
                values
                 (:corp_num, :start_event_id, :can_jur_typ_cd, TO_DATE(:cont_out_dt, 'YYYY-mm-dd'),
                  :othr_juri_desc, :home_company_nme)
                """,
                corp_num=cont_out_obj.corp_num,
                start_event_id=cont_out_obj.start_event_id,
                can_jur_typ_cd=cont_out_obj.can_jur_typ_cd,
                cont_out_dt=cont_out_obj.cont_out_dt,
                othr_juri_desc=cont_out_obj.othr_juri_desc,
                home_company_nme=cont_out_obj.home_company_nme,
            )

        except Exception as err:
            current_app.logger.error(f'Error inserting cont_out for event {cont_out_obj.event_id}.')
            raise err

    @classmethod
    def get_by_event(cls, cursor, event_id: str) -> List[ContOut]:
        """Get the cont out with the given event id."""
        querystring = (
            """
            select corp_num, start_event_id, can_jur_typ_cd, cont_out_dt, othr_juri_desc, home_company_nme
            from cont_out
            where start_event_id=:event_id
            """
        )

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=event_id)
            return cls._create_cont_out_objs(cursor=cursor)

        except Exception as err:
            current_app.logger.error(f'error getting cont_out for event {event_id}')
            raise err
