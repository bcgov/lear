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
from flask import current_app

from colin_api.exceptions import GenericException
from colin_api.resources.db import DB


class EntityName:
    """Entity name object."""

    legal_name = None
    event_id = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'legalName': self.legal_name,
            'eventId': self.event_id
        }

    @classmethod
    def _create_name_obj(cls, cursor, identifier: str = None):
        """Return a EntityName obj by parsing cursor."""
        corp_name_info = cursor.fetchone()
        if not corp_name_info:
            raise GenericException(error=f'{identifier} name not found', status_code=404)

        test_second_name = cursor.fetchone()
        if test_second_name:
            current_app.logger.error(f'Got more than 1 current name for {identifier}')

        corp_name_info = dict(zip([x[0].lower() for x in cursor.description], corp_name_info))

        name_obj = EntityName()
        name_obj.legal_name = corp_name_info['corp_nme']
        name_obj.event_id = corp_name_info['start_event_id']

        return name_obj

    @classmethod
    def get_current(cls, identifier: str = None):
        """Get current entity name."""
        if not identifier:
            return None

        querystring = ("""
            select start_event_id, corp_name
            from corp_name
            where corp_num=:identifier and end_event_id is null
            """)

        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, identifier=identifier)

            return cls._create_name_obj(cursor=cursor, identifier=identifier)

        except Exception as err:
            current_app.logger.error('error getting entity name for corp: {}'.format(identifier))
            raise err

    @classmethod
    def get_by_event(cls, identifier: str = None, event_id: str = None):
        """Get the entity name corresponding with the given event id."""
        if not identifier or not event_id:
            return None

        querystring = ("""
            select start_event_id, corp_nme
            from corp_name
            where corp_num=:identifier and start_event_id=:event_id
            """)

        try:
            cursor = DB.connection.cursor()
            cursor.execute(querystring, identifier=identifier, event_id=event_id)

            return cls._create_name_obj(cursor=cursor, identifier=identifier)

        except Exception as err:
            current_app.logger.error('error getting entity name for corp: {}'.format(identifier))
            raise err
