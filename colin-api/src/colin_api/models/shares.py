# Copyright © 2020 Province of British Columbia
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

class Share:
    share_id = None
    max_number_shares = None
    has_max_shares = None
    has_special_rights = None
    share_name = None

    def to_dict(self):
        return None

class ShareClass(Share):
    currency_type = None
    has_par_value = None
    par_value_amt = None
    series = None

    def to_dict(self):
        return None

class ShareObject:

    share_classes = None

    @classmethod
    def _build_shares_list(cls, cursor, corp_num):
        share_classes = []

        share_struct = cursor.fetchall()

        for row in share_struct:
            share_classes.append(cls._get_share_classes(cursor, row.get('event_id'), corp_num))

        return share_classes

    @classmethod
    def _get_share_classes(cls, cursor, event_id, corp_num):
        query = ""
        share_classes = []
        cursor.execute(query)
        class_arr = cursor.fetchall()
        
        description = cursor.description

        for row in class_arr:
             row = dict(zip([x[0].lower() for x in description], row))
             share_class = ShareClass()
             share_class.currency_type = row['']
             share_class.has_max_shares = row['']
             share_class.has_special_rights = row['']
             share_class.has_par_value = row['']
             share_class.share_id = row['']
             share_class.share_name = row['']
             share_class.par_value_amt = row['']
             share_class.max_number_shares = row['']
             share_class.series = cls._get_share_series(cursor, share_class, corp_num)
             share_classes.append(share_class)

        return share_classes

    @classmethod
    def _get_share_series(cls, cursor, share_class, identifier):
        query = ""
        share_series = []
        cursor.execute(query)
        series_arr = cursor.fetchall()
        
        description = cursor.description

        for row in series_arr:
            row = dict(zip([x[0].lower() for x in description], row))
            series = Share()
            series.has_max_shares = row['']
            series.has_special_rights = row['']
            series.max_number_shares = row['']
            series.share_id = row['']
            series.share_name = row['']
            share_series.append(series)

        return share_series

    @classmethod
    def get_all(cls, cursor, identifier: str = None):
        """Return all share structure entries for this business."""
        # Add business NME to all queries
        query = """select start_event_id from share_struct where corp_num=:identifier
                   and end_event_id is null"""

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(
                query,
                identifier=identifier
            )
            share_list = cls._build_shares_list(cursor, identifier)

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error('error getting current parties info for {}'.format(identifier))
            raise err

        if not share_list:
            return None

        return share_list

    @classmethod
    def get_by_event(cls, cursor, identifier: str = None, event_id: int = None):
        return None

    @classmethod
    def create_share_structure(cls, business):
        return None