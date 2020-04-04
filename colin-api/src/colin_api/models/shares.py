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
        return {
                'id': self.share_id,
                'name': self.share_name,
                'shareStructureType': 'Series',
                'displayOrder': self.share_id,
                'maxNumberOfShares': self.max_number_shares,
                'hasMaximumShares': self.has_max_shares == 'Y' or False,
                'hasRightsOrRestrictions': self.has_special_rights == 'Y' or False,
            }

class ShareClass(Share):
    currency_type = None
    has_par_value = None
    par_value_amt = None
    series = None
 
    def to_dict(self):
        return {
                'id': self.share_id,
                'name': self.share_name,
                'shareStructureType': 'Class',
                'displayOrder': self.share_id,
                'maxNumberOfShares': self.max_number_shares,
                'parValue': self.par_value_amt,
                'currency': self.currency_type,
                'hasMaximumShares': self.has_max_shares == 'Y' or False,
                'hasParValue': self.has_par_value == 'Y' or False,
                'hasRightsOrRestrictions': self.has_special_rights == 'Y' or False,
                'series': [
                    x.to_dict() for x in self.series
                ]
        }
        

class ShareObject:

    share_classes = None

    @classmethod
    def _build_shares_list(cls, cursor, corp_num):
        share_classes = []

        share_struct = cursor.fetchall()

        for row in share_struct:
            share_classes.append(cls._get_share_classes(cursor, row[0], corp_num))

        return share_classes

    @classmethod
    def _get_share_classes(cls, cursor, event_id, corp_num):
        query = """select share_class_id, currency_typ_cd, max_share_ind, share_quantity, spec_rights_ind,
                   par_value_ind, par_value_amt, class_nme, other_currency from share_struct_cls
                   where start_event_id=:event_id and corp_num=:corp_num"""

        share_classes = []
        cursor.execute(query,
                       corp_num=corp_num, event_id=event_id)
        class_arr = cursor.fetchall()
        
        description = cursor.description

        for row in class_arr:
             row = dict(zip([x[0].lower() for x in description], row))
             share_class = ShareClass()
             share_class.currency_type = row['currency_typ_cd']
             share_class.has_max_shares = row['max_share_ind']
             share_class.has_special_rights = row['spec_rights_ind']
             share_class.has_par_value = row['par_value_ind']
             share_class.share_id = row['share_class_id']
             share_class.share_name = row['class_nme']
             share_class.par_value_amt = row['par_value_amt']
             share_class.max_number_shares = row['share_quantity']
             share_class.series = cls._get_share_series(cursor, share_class, corp_num)
             share_classes.append(share_class)

        return share_classes

    @classmethod
    def _get_share_series(cls, cursor, share_class, identifier):
        query = """select series_id, max_share_ind, share_quantity, spec_right_ind,
                    series_nme from share_series where share_class_id=:class_id and 
                    corp_num=:identifier"""

        share_series = []
        cursor.execute(query,
                       class_id=share_class.share_id,
                       identifier=identifier
                       )

        series_arr = cursor.fetchall()
        
        description = cursor.description

        for row in series_arr:
            row = dict(zip([x[0].lower() for x in description], row))
            series = Share()
            series.has_max_shares = row['max_share_ind']
            series.has_special_rights = row['spec_right_ind']
            series.max_number_shares = row['share_quantity']
            series.share_id = row['series_id']
            series.share_name = row['series_nme']
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
    def create_share_structure(cls, cursor, business, event_id, share_dict):
        query = """insert into share_struct (corp_num, start_event_id, dd_corp_num)
                   values (:corp_num, :event_id, :corp_num)
                """

        cursor.execute(
                query,
                corp_num=business.identifier, event_id=event_id
            )

        for share_class in share_dict:
            cls.create_share_class(cursor, event_id, business, share_class)
 
        return None
    # Todo Add exceptions/error handling
    @classmethod
    def create_share_class(cls, cursor, event_id, business, class_dict):
        query = """insert into share_struct_cls (corp_num, share_class_id, start_event_id,
                    currency_typ_cd, max_share_ind, share_quantity, spec_rights_ind,
                    par_value_ind, par_value_amt, class_nme values (
                    :corp_num, :class_id, :event_id, :currency, :has_max_share,
                    :qty, :has_spec_rights, :has_par_value, :par_value, :name
                    )"""
        
        cursor.execute(
                query,
                corp_num=business.identifier, 
                class_id=class_dict['id'],
                event_id=event_id,
                currency=class_dict['currency'],
                has_max_share=class_dict['hasMaximumShares'],
                qty=class_dict['maxNUmberOfShares'],
                has_spec_rights=class_dict['hasRightsOrRestrictions'],
                has_par_value=class_dict['hasParValue'],
                par_value=class_dict['parValue']
            )

        for share_series in class_dict['series']:
            cls.create_share_series(cursor, event_id, business, class_dict['id'], share_series)

        return None
    
    @classmethod
    def create_share_series(cls, cursor, event_id, business, class_id, series_arr):
        return None
