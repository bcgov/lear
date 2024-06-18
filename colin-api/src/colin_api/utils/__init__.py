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
"""Time conversion methods."""
import datetime

from flask import current_app
from pytz import timezone


def convert_to_json_date(thedate: datetime.datetime) -> str:
    """Convert datetime to string formatted as YYYY-MM-DD, per JSON Schema specs."""
    if not thedate:
        return None
    try:
        return thedate.strftime('%Y-%m-%d')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.debug(f'Tried to convert {thedate}, but failed: {err}')
        return None


def convert_to_json_datetime(thedate: datetime.datetime) -> str:
    """Convert datetime to string formatted as YYYY-MM-SSTHH:MM:SS+00:00, per JSON Schema specs."""
    if not thedate:
        return None
    try:
        # timezone info not in var (they are pacific times so add timezone)
        thedate = datetime.datetime(thedate.year,
                                    thedate.month,
                                    thedate.day,
                                    thedate.hour,
                                    thedate.minute,
                                    thedate.second)
        # treat date as naive date and add timezone by using localize function
        thedate = timezone('US/Pacific').localize(thedate)
        # convert to utc time
        thedate = thedate.astimezone(timezone('UTC'))
        # return as string
        return thedate.strftime('%Y-%m-%dT%H:%M:%S-00:00')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.debug(f'Tried to convert {thedate}, but failed: {err}')
        return None


def convert_to_pacific_time(thedate: str) -> str:
    """Convert the datetime string to pacific time string."""
    try:
        # tries converting two formats before bailing
        try:
            datetime_obj = datetime.datetime.strptime(thedate, '%Y-%m-%dT%H:%M:%S.%f+00:00')
        except Exception:  # pylint: disable=broad-except;
            datetime_obj = datetime.datetime.strptime(thedate, '%Y-%m-%dT%H:%M:%S+00:00')
        datetime_utc = datetime_obj.replace(tzinfo=timezone('UTC'))
        datetime_pst = datetime_utc.astimezone(timezone('US/Pacific'))
        return datetime_pst.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.error(f'Tried to convert {thedate}, but failed: {err}')
        raise err


def stringify_list(list_orig: list) -> str:
    """Stringify the given list for sql query - used when inserting lists for reset query's."""
    list_str = ''
    for item in list_orig:
        # remove any spaces or end brackets to avoid sql injection that could end the list and execute another command
        list_str += ("'" + str(item) + "',").replace(' ', '').replace(')', '')
    if list_str:
        list_str = list_str[:-1]
    return list_str


def delete_from_table_by_event_ids(cursor, event_ids: list, table: str, column: str = 'start_event_id'):
    """Delete rows with given event ids from given table."""
    try:
        # table is a value set by the code: not possible to be sql injected from a request
        cursor.execute(f"""
            DELETE FROM {table}
            WHERE {column} in ({stringify_list(event_ids)})
        """)
    except Exception as err:
        current_app.logger.error(f'Error in Reset: Failed to delete rows for events {event_ids} in table: {table}')
        raise err


def get_max_value(cursor, corp_num: str, table: str, column: str):
    """Get the max value for a column in a table for a business."""
    try:
        cursor.execute(
            f"""
            select max({column}) from {table} where corp_num=:corp_num
            """,
            corp_num=corp_num
        )
        return cursor.fetchone()[0]

    except Exception as err:
        current_app.logger.error(f'Error getting max {column}.')
        raise err


def convert_to_snake(inputstring: str):
    """Convert inputstring from camel case to snake case."""
    return ''.join('_' + char.lower() if char.isupper() else char for char in inputstring).lstrip('_')
