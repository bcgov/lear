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
from flask import current_app


def convert_to_json_date(thedate):
    """Convert datetime to string formatted as YYYY-MM-DD, per JSON Schema specs.

    :param thedate: datetime object
    :return: string
    """
    if not thedate:
        return None
    try:
        return thedate.strftime('%Y-%m-%d')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.debug('Tried to convert {date}, but failed: {error}'.format(date=thedate, error=err))
        return None


def convert_to_json_datetime(thedate):
    """Convert datetime to string formatted as YYYY-MM-SSTHH:MM:SS+00:00, per JSON Schema specs.

    :param thedate: datetime object
    :return: string
    """
    if not thedate:
        return None
    try:
        return thedate.strftime('%Y-%m-%dT%H:%M:%S-00:00')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.debug('Tried to convert {date}, but failed: {error}'.format(date=thedate, error=err))
        return None


def stringify_list(list_orig: list):
    """Stringify the given list for sql query - used when inserting lists for reset query's."""
    list_str = ''
    for item in list_orig:
        # remove any spaces or end brackets to avoid sql injection that could end the list and execute another command
        list_str += ("'" + str(item) + "',").replace(' ', '').replace(')', '')
    if list_str:
        list_str = list_str[:-1]
    return list_str


def delete_from_table_by_event_ids(cursor, event_ids: list, table: str):
    """Delete rows with given event ids from given table."""
    try:
        # table is a value set by the code: not possible to be sql injected from a request
        cursor.execute(f"""
            DELETE FROM {table}
            WHERE start_event_id in ({stringify_list(event_ids)})
        """)
    except Exception as err:
        current_app.logger.error(f'Error in Reset: Failed to delete rows for events {event_ids} in table: {table}')
        raise err
