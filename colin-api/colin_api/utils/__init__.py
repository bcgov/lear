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
    try:
        return thedate.strftime('%Y-%m-%dT%H:%M:%S-00:00')
    except Exception as err:  # pylint: disable=broad-except; want to return None in all cases where convert failed
        current_app.logger.debug('Tried to convert {date}, but failed: {error}'.format(date=thedate, error=err))
        return None
