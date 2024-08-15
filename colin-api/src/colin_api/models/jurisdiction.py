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
"""Meta information about the service.

Currently this only provides API versioning information
"""
from __future__ import annotations

from typing import List

from flask import current_app

from colin_api.resources.db import DB


class Jurisdiction:
    """Jurisdiction object."""

    corp_num = None
    start_event_id = None
    can_jur_typ_cd = None
    xpro_typ_cd = None  # COR
    home_recogn_dt = None
    othr_juris_desc = None
    home_juris_num = None
    bc_xpro_num = None
    home_company_nme = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'corpNum': self.corp_num,
            'startEventId': self.start_event_id,
            'canJurTypCd': self.can_jur_typ_cd,
            'xproTypCd': self.xpro_typ_cd,
            'homeRecognDt': self.home_recogn_dt,
            'othrJurisDesc': self.othr_juris_desc,
            'homeJurisNum': self.home_juris_num,
            'bcXproNum': self.bc_xpro_num,
            'homeCompanyNme': self.home_company_nme,
        }

    @classmethod
    def _create_jurisdiction_objs(cls, cursor) -> List:
        """Return a Jurisdiction obj by parsing cursor."""
        jurisdictions = cursor.fetchall()

        jurisdiction_objs = []
        for jurisdiction in jurisdictions:
            jurisdiction = dict(zip([x[0].lower() for x in cursor.description], jurisdiction))
            jurisdiction_obj = Jurisdiction()
            jurisdiction_obj.corp_num = jurisdiction['corp_num']
            jurisdiction_obj.start_event_id = jurisdiction['start_event_id']
            jurisdiction_obj.can_jur_typ_cd = jurisdiction['can_jur_typ_cd']
            jurisdiction_obj.xpro_typ_cd = jurisdiction['xpro_typ_cd']
            jurisdiction_obj.home_recogn_dt = jurisdiction['home_recogn_dt']
            jurisdiction_obj.othr_juris_desc = jurisdiction['othr_juris_desc']
            jurisdiction_obj.home_juris_num = jurisdiction['home_juris_num']
            jurisdiction_obj.bc_xpro_num = jurisdiction['bc_xpro_num']
            jurisdiction_obj.home_company_nme = jurisdiction['home_company_nme']
            jurisdiction_objs.append(jurisdiction_obj)

        return jurisdiction_objs

    @classmethod
    def create_jurisdiction(cls, cursor, jurisdiction_obj) -> Jurisdiction:
        """Add record to the JURISDICTION table."""
        try:
            cursor.execute(
                """
                insert into JURISDICTION (CORP_NUM, START_EVENT_ID, CAN_JUR_TYP_CD, XPRO_TYP_CD, HOME_RECOGN_DT,
                  OTHR_JURIS_DESC, HOME_JURIS_NUM, BC_XPRO_NUM, HOME_COMPANY_NME)
                values 
                 (:corp_num, :start_event_id, :can_jur_typ_cd, :xpro_typ_cd, TO_DATE(:home_recogn_dt, 'YYYY-mm-dd'),
                  :othr_juris_desc, :home_juris_num, :bc_xpro_num, :home_company_nme)
                """,
                corp_num=jurisdiction_obj.corp_num,
                start_event_id=jurisdiction_obj.start_event_id,
                can_jur_typ_cd=jurisdiction_obj.can_jur_typ_cd,
                xpro_typ_cd=jurisdiction_obj.xpro_typ_cd,
                home_recogn_dt=jurisdiction_obj.home_recogn_dt,
                othr_juris_desc=jurisdiction_obj.othr_juris_desc,
                home_juris_num=jurisdiction_obj.home_juris_num,
                bc_xpro_num=jurisdiction_obj.bc_xpro_num,
                home_company_nme=jurisdiction_obj.home_company_nme,
            )

        except Exception as err:
            current_app.logger.error(f'Error inserting jurisdiction for event {jurisdiction_obj.event_id}.')
            raise err

    @classmethod
    def get_by_event(cls, cursor, event_id: str) -> List[Jurisdiction]:
        """Get the jurisdiction with the given event id."""
        querystring = (
            """
            select corp_num, start_event_id, can_jur_typ_cd, xpro_typ_cd, home_recogn_dt, othr_juris_desc,
	        home_juris_num, bc_xpro_num, home_company_nme
            from jurisdiction
            where start_event_id=:event_id
            """
        )

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=event_id)
            return cls._create_jurisdiction_objs(cursor=cursor)

        except Exception as err:
            current_app.logger.error(f'error getting jurisdiction for event {event_id}')
            raise err
