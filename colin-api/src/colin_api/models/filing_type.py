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

from typing import List, Optional

from flask import current_app

from colin_api.resources.db import DB
from colin_api.utils import stringify_list


# pylint: disable=too-few-public-methods
class FilingType:
    """Filing Type object."""

    FILING_TYPE_QUERY = (
        """
            select ft.filing_typ_cd, ft.short_desc, ft.full_desc
            from filing_type ft
        """
    )

    filing_typ_cd = None
    short_desc = None
    full_desc = None

    def __init__(self):
        """Initialize with all values None."""

    @classmethod
    def _create_filing_type_objs(cls, cursor) -> List:
        """Return a Filing Type obj by parsing cursor."""
        filing_types = cursor.fetchall()

        filing_type_objs = []
        for filing_type_info in filing_types:
            filing_type_info = dict(zip([x[0].lower() for x in cursor.description], filing_type_info))
            filing_type_obj = FilingType()
            filing_type_obj.filing_typ_cd = filing_type_info['filing_typ_cd']
            filing_type_obj.short_desc = filing_type_info['short_desc']
            filing_type_obj.full_desc = filing_type_info['full_desc']
            filing_type_objs.append(filing_type_obj)

        return filing_type_objs

    @classmethod
    def get_most_recent_match_before_event(cls,
                                           cursor,
                                           corp_num: str,
                                           event_id: str,
                                           matching_filing_types: List) -> Optional[FilingType]:
        """Get most recent match of any one of filing types provided before a given event id for a specific corp num."""
        try:
            if not cursor:
                cursor = DB.connection.cursor()

            condition = f"""
                JOIN FILING f ON (ft.FILING_TYP_CD = f.FILING_TYP_CD)
                JOIN EVENT e ON (f.EVENT_ID = e.EVENT_ID)
                WHERE e.CORP_NUM = :corp_num
                  AND e.EVENT_TYP_CD = 'FILE'
                  AND e.EVENT_ID < :event_id
                  AND f.FILING_TYP_CD in ({stringify_list(matching_filing_types)})
                  and rownum = 1
                order by f.EVENT_ID asc
            """

            querystring = cls.FILING_TYPE_QUERY + condition
            cursor.execute(querystring, corp_num=corp_num, event_id=event_id)

            results = cls._create_filing_type_objs(cursor=cursor)
            num_results = len(results)
            result = results[0] if num_results and num_results > 0 else None
            return result

        except Exception as err:
            current_app.logger.error(f'error getting filing type for {corp_num} by event {event_id}')
            raise err
