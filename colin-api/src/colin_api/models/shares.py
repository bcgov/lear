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
from __future__ import annotations

from typing import List, Optional

from flask import current_app

from colin_api.resources.db import DB
from colin_api.utils import delete_from_table_by_event_ids, get_max_value


class Share:  # pylint: disable=too-many-instance-attributes;
    """Base Share Object."""

    # pylint: disable=too-few-public-methods;
    share_id = None
    max_number_shares = None
    has_max_shares = None
    has_special_rights = None
    share_name = None
    priority = 0

    def __init__(self):
        """Initialize with all values None."""

    def to_dict(self):
        """Return Share Series as a Dictionary."""
        return {
            'id': self.share_id,
            'name': self.share_name,
            'shareStructureType': 'Series',
            'displayOrder': self.share_id,
            'maxNumberOfShares': self.max_number_shares,
            'hasMaximumShares': self.has_max_shares == 'N' or False,
            'hasRightsOrRestrictions': self.has_special_rights == 'Y' or False,
            'priority': self.priority
        }


class ShareClass(Share):  # pylint: disable=too-many-instance-attributes;
    """Share Class Object."""

    # pylint: disable=too-few-public-methods
    currency_type = None
    has_par_value = None
    par_value_amt = None
    series = None

    def __init__(self):
        """Initialize with all values None."""
        Share.__init__(self)

    def to_dict(self):
        """Return Share Class as a Dictionary."""
        return {
            'id': self.share_id,
            'name': self.share_name,
            'shareStructureType': 'Class',
            'priority': self.priority,
            'displayOrder': self.share_id,
            'maxNumberOfShares': self.max_number_shares,
            'parValue': self.par_value_amt,
            'currency': self.currency_type,
            'hasMaximumShares': self.has_max_shares == 'N' or False,
            'hasParValue': self.has_par_value == 'Y' or False,
            'hasRightsOrRestrictions': self.has_special_rights == 'Y' or False,
            'series': [
                x.to_dict() for x in self.series
            ]
        }


class ShareObject:  # pylint: disable=too-many-instance-attributes;
    """Share Object for Share Structure, contains factory/helper methods."""

    # pylint: disable=too-few-public-methods
    start_event_id = None
    end_event_id = None
    share_classes = None

    def __init__(self):
        """Initialize with all values None."""

    def to_dict(self):
        """Return Share Structure as a Dictionary."""
        return {
            'shareClasses': [
                x.to_dict() for x in self.share_classes
            ]
        }

    @classmethod
    def _build_shares_list(cls, cursor, corp_num: str) -> List:
        """Build and format the share structure for corp."""
        to_return = []

        share_structs = cursor.fetchall()
        for row in share_structs:
            share_structure = ShareObject()
            share_structure.start_event_id = row[0]
            share_structure.end_event_id = row[1]
            share_structure.share_classes = cls._get_share_classes(cursor, share_structure.start_event_id, corp_num)
            to_return.append(share_structure)

        return to_return

    @classmethod
    def _get_share_classes(cls, cursor, event_id, corp_num):
        """Retrieve Share Classes for Corp."""
        query = """select share_class_id, currency_typ_cd, max_share_ind, share_quantity, spec_rights_ind,
                   par_value_ind, par_value_amt, class_nme, other_currency from share_struct_cls
                   where start_event_id=:event_id and corp_num=:corp_num"""

        share_classes = []

        try:
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

        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to retrieve Share Classes for {corp_num}')
            raise err

        return share_classes

    @classmethod
    def _get_share_series(cls, cursor, share_class, identifier):
        """Retrieve Share Series for Corp."""
        query = """select series_id, max_share_ind, share_quantity, spec_right_ind,
                    series_nme from share_series where share_class_id=:class_id and
                    corp_num=:identifier"""

        share_series = []
        try:
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

        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to retrieve Share Series for {identifier}')
            raise err

        return share_series

    @classmethod
    def get_all(cls, cursor, corp_num: str, event_id: str = None) -> Optional[List, ShareObject]:
        """Return all share structure entries for this business (Optional: return all for specific share structure)."""
        # Add business NME to all queries
        query = 'select start_event_id, end_event_id from share_struct where corp_num=:corp_num'

        if event_id:
            query += f' and start_event_id={event_id}'
        else:
            query += ' and end_event_id is null'
        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute(
                query,
                corp_num=corp_num
            )
            share_list = cls._build_shares_list(cursor, corp_num)
            if not share_list:
                return None

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'error getting share structure for {corp_num}')
            raise err

        if event_id:
            if len(share_list) > 1:
                current_app.logger.error(
                    f'More than 1 active share structure for {corp_num}. This will cause unknown consequences.')
            return share_list[0]

        return share_list

    @classmethod
    def create_share_structure(cls, cursor, corp_num: str, event_id: str, shares_list: list):
        """Create share structure entry for corporation."""
        query = (
            """
            insert into share_struct (corp_num, start_event_id, dd_corp_num)
            values (:corp_num, :event_id, :corp_num)
            """
        )
        try:
            cursor.execute(
                query,
                corp_num=corp_num,
                event_id=event_id
            )
        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to create Share Structure for {corp_num}')
            raise err

        max_class_id = get_max_value(cursor, corp_num=corp_num, table='share_struct_cls', column='share_class_id')
        class_id = max_class_id + 1 if max_class_id else 0
        for share_class in shares_list:
            cls.create_share_class(cursor, event_id, corp_num, class_id, share_class)
            class_id = class_id + 1

    @classmethod
    def create_share_class(cls, cursor, event_id: str, corp_num: str, class_id: int, class_dict: dict):
        # pylint: disable=too-many-arguments
        """Create Share Classes for corp."""
        query = (
            """
            insert into share_struct_cls (corp_num, share_class_id, start_event_id, currency_typ_cd, max_share_ind,
                share_quantity, spec_rights_ind, par_value_ind, par_value_amt, class_nme)
            values (:corp_num, :class_id, :event_id, :currency, :has_max_share, :qty, :has_spec_rights, :has_par_value,
                :par_value, :name)
            """
        )
        try:
            currency = class_dict.get('currency', '')
            if currency and currency not in ('CAD', 'USD', 'GBP', 'EUR', 'JPY'):
                currency = 'OTH'

            cursor.execute(
                query,
                corp_num=corp_num,
                class_id=class_id,
                event_id=event_id,
                currency=currency,
                has_max_share='N' if class_dict['hasMaximumShares'] else 'Y',
                qty=class_dict['maxNumberOfShares'],
                has_spec_rights='Y' if class_dict['hasRightsOrRestrictions'] else 'N',
                has_par_value='Y' if class_dict['hasParValue'] else 'N',
                par_value=class_dict.get('parValue', ''),
                name=class_dict['name']
            )
        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to create Share Classes for {corp_num}')
            raise err

        series_id = 0
        for share_series in class_dict.get('series', []):
            cls.create_share_series(cursor, event_id, corp_num, class_id, series_id, share_series)
            series_id = series_id + 1

    @classmethod
    def create_share_series(
            cls, cursor, event_id: str, corp_num: str, class_id: str, series_id: int, series_dict: dict):
        # pylint: disable=too-many-arguments
        """Insert Share Series for Share Class and Corp."""
        query = (
            """
            insert into share_series (corp_num, share_class_id, series_id, start_event_id, max_share_ind,
                share_quantity, spec_right_ind, series_nme)
            values (:corp_num, :class_id, :series_id, :event_id, :has_max_share, :qty, :has_spec_rights, :name)
            """
        )
        try:
            cursor.execute(
                query,
                corp_num=corp_num,
                class_id=class_id,
                series_id=series_id,
                event_id=event_id,
                has_max_share='N' if series_dict['hasMaximumShares'] else 'Y',
                qty=series_dict['maxNumberOfShares'],
                has_spec_rights='Y' if series_dict['hasRightsOrRestrictions'] else 'N',
                name=series_dict['name']
            )
        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to create Share Series for {corp_num}')
            raise err

    @classmethod
    def end_share_structure(cls, cursor, event_id: str, corp_num: str):
        """End Share Struct for a corp."""
        try:
            cursor.execute(
                """
                update share_struct
                set end_event_id=:event_id
                where corp_num=:corp_num and end_event_id is null
                """,
                corp_num=corp_num,
                event_id=event_id
            )
        except Exception as err:
            current_app.logger.error(f'Error in Share Structure: Failed to create Share Structure for {corp_num}')
            raise err

    @classmethod
    def delete_shares(cls, cursor, event_ids):
        """Delete Share Structure by event id."""
        # Remove share series
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids,
                                       table='share_series', column='start_event_id')

        # Remove share classes
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids,
                                       table='share_struct_cls', column='start_event_id')

        # Remove share structure
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids,
                                       table='share_struct', column='start_event_id')
