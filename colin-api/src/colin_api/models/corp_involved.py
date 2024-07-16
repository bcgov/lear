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


class CorpInvolved:
    """Corp Involved object."""

    event_id = None
    corp_involve_id = None
    corp_num = None
    can_jur_typ_cd = None
    adopted_corp_ind = None
    home_juri_num = None
    othr_juri_desc = None
    foreign_nme = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'eventId': self.event_id,
            'corpInvolveId': self.corp_involve_id,
            'corpNum': self.corp_num,
            'canJurTypCd': self.can_jur_typ_cd,
            'adoptedCorpInd': self.adopted_corp_ind,
            'homeJuriNum': self.home_juri_num,
            'othrJuriDesc': self.othr_juri_desc,
            'foreignName': self.foreign_nme,
        }

    @classmethod
    def _create_corp_involved_objs(cls, cursor) -> List:
        """Return a CorpInvolved obj by parsing cursor."""
        corps_involved = cursor.fetchall()

        corp_involved_objs = []
        for corp_involved in corps_involved:
            corp_involved = dict(zip([x[0].lower() for x in cursor.description], corp_involved))
            corp_involved_obj = CorpInvolved()
            corp_involved_obj.event_id = corp_involved['event_id']
            corp_involved_obj.corp_involve_id = corp_involved['corp_involve_id']
            corp_involved_obj.corp_num = corp_involved['corp_num']
            corp_involved_obj.can_jur_typ_cd = corp_involved['can_jur_typ_cd']
            corp_involved_obj.adopted_corp_ind = corp_involved['adopted_corp_ind']
            corp_involved_obj.home_juri_num = corp_involved['home_juri_num']
            corp_involved_obj.othr_juri_desc = corp_involved['othr_juri_desc']
            corp_involved_obj.foreign_nme = corp_involved['foreign_nme']
            corp_involved_objs.append(corp_involved_obj)

        return corp_involved_objs

    @classmethod
    def create_corp_involved(cls, cursor, corp_involved_obj) -> CorpInvolved:
        """Add record to the CORP INVOLVED table."""
        try:
            cursor.execute(
                """
                insert into CORP_INVOLVED (EVENT_ID, CORP_INVOLVE_ID, CORP_NUM, CAN_JUR_TYP_CD, ADOPTED_CORP_IND,
                    HOME_JURI_NUM, OTHR_JURI_DESC, FOREIGN_NME)
                values (:event_id, :corp_involve_id, :corp_num, :can_jur_typ_cd, :adopted_corp_ind, 
                    :home_juri_num, :othr_juri_desc, :foreign_nme)
                """,
                event_id=corp_involved_obj.event_id,
                corp_involve_id=corp_involved_obj.corp_involve_id,
                corp_num=corp_involved_obj.corp_num,
                can_jur_typ_cd=corp_involved_obj.can_jur_typ_cd,
                adopted_corp_ind=corp_involved_obj.adopted_corp_ind,
                home_juri_num=corp_involved_obj.home_juri_num,
                othr_juri_desc=corp_involved_obj.othr_juri_desc,
                foreign_nme=corp_involved_obj.foreign_nme,
            )

        except Exception as err:
            current_app.logger.error(f'Error inserting corp involved for event {corp_involved_obj.event_id}.')
            raise err

    @classmethod
    def get_by_event(cls, cursor, event_id: str) -> List[CorpInvolved]:
        """Get the corps involved with the given event id."""
        querystring = (
            """
            select event_id, corp_involve_id, corp_num, can_jur_typ_cd, adopted_corp_ind, home_juri_num, 
            othr_juri_desc, foreign_nme, dd_event_id
            from corp_involved
            where event_id=:event_id
            """
        )

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(querystring, event_id=event_id)
            return cls._create_corp_involved_objs(cursor=cursor)

        except Exception as err:
            current_app.logger.error(f'error getting corp involved for event {event_id}')
            raise err
