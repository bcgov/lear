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
from typing import Dict, List, Optional

from flask import current_app

from colin_api.models import Address  # pylint: disable=cyclic-import
from colin_api.resources.db import DB
from colin_api.utils import delete_from_table_by_event_ids, stringify_list


class Office:
    """Registered office object."""

    OFFICE_TYPES_CODES = {
        'RG': 'registeredOffice',
        'RC': 'recordsOffice',
        'LQ': 'liquidationOffice',
        'DS': 'custodialOffice',
        'registeredOffice': 'RG',
        'recordsOffice': 'RC',
        'liquidationOffice': 'LQ',
        'custodialOffice': 'DS'
    }

    delivery_address = None
    mailing_address = None
    event_id = None
    end_event_id = None
    office_type = None
    office_code = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            self.office_type: {
                'deliveryAddress': self.delivery_address,
                'mailingAddress': self.mailing_address
            }
        }

    @classmethod
    def _build_offices_list(
            cls, cursor, querystring: str, identifier: str = None, event_id: str = None) -> Optional[List]:
        """Return the office objects for the given query."""
        if not cursor:
            cursor = DB.connection.cursor()
        if identifier:
            cursor.execute(querystring, identifier=identifier)
        else:
            cursor.execute(querystring, event_id=event_id)
        office_info = cursor.fetchall()
        offices = []
        if not office_info:
            return None

        description = cursor.description
        for office_item in office_info:
            office = dict(zip([x[0].lower() for x in description], office_item))
            office_obj = Office()
            office_obj.office_type = cls.OFFICE_TYPES_CODES.get(office['office_typ_cd'], None)
            if office_obj.office_type:
                office_obj.event_id = office['start_event_id']
                office_obj.end_event_id = office['end_event_id']
                office_obj.delivery_address = Address.get_by_address_id(cursor, office['delivery_addr_id']).as_dict()
                office_obj.office_code = office['office_typ_cd']
                if office['mailing_addr_id']:
                    office_obj.mailing_address = Address.get_by_address_id(cursor, office['mailing_addr_id']).as_dict()
                else:
                    office_obj.mailing_address = office_obj.delivery_address
                offices.append(office_obj)

        return offices

    @classmethod
    def convert_obj_list(cls, office_obj_list: list = None):
        """Return converted list of given office objects as one dict."""
        if not office_obj_list:
            return None

        offices_dict = {}
        for office_obj in office_obj_list:
            if office_obj.office_type not in offices_dict.keys():  # pylint: disable=consider-iterating-dictionary
                offices_dict.update(office_obj.as_dict())
            else:
                current_app.logger.error(f'Received more than 1 office for {office_obj.office_type}')
        return offices_dict

    @classmethod
    # pylint: disable=too-many-arguments; one extra
    def create_new_office(cls, cursor, addresses: Dict, event_id: str, corp_num: str, office_type: str):
        """Create row for new office and end old one.

        addresses.keys() = ['deliveryAddress', 'mailingAddress']
        """
        delivery_addr_id = Address.create_new_address(cursor, addresses['deliveryAddress'], corp_num=corp_num)
        mailing_addr_id = Address.create_new_address(cursor, addresses['mailingAddress'], corp_num=corp_num)
        office_code = Office.OFFICE_TYPES_CODES[office_type]

        # update office table to include new addresses and end old office
        update_dict = {
            'new_event_id': event_id,
            'corp_num': corp_num,
            'new_delivery_addr_id': delivery_addr_id,
            'new_mailing_addr_id': mailing_addr_id,
            'office_code': office_code
        }
        Office.update_office(cursor=cursor, office_info=update_dict)

    @classmethod
    def get_current(cls, cursor, identifier: str = None):
        """Return current registered and/or records office addresses."""
        if not identifier:
            return None

        querystring = """
            select start_event_id, end_event_id, mailing_addr_id, delivery_addr_id, office_typ_cd
            from office
            where corp_num=:identifier and end_event_id is null
            """

        try:
            offices = cls._build_offices_list(cursor, querystring=querystring, event_id=None, identifier=identifier)
            return offices
        except Exception as err:
            current_app.logger.error(f'error getting office for corp: {identifier}')
            raise err

    @classmethod
    def get_by_event(cls, cursor, event_id: str = None):
        """Return current registered and/or records office address."""
        if not event_id:
            return None

        querystring = """
            select start_event_id, end_event_id, mailing_addr_id, delivery_addr_id, office_typ_cd
            from office
            where start_event_id=:event_id
            """

        try:
            offices = cls._build_offices_list(cursor, querystring=querystring, identifier=None, event_id=event_id)
            return offices

        except Exception as err:  # pylint: disable=broad-except; want to catch all errs
            current_app.logger.error(f'error getting office from event : {event_id}')

            raise err

    @classmethod
    def end_office(cls, cursor, event_id: str, corp_num: str, office_code: str):
        """Update old office with end event id."""
        try:
            cursor.execute(
                """
                UPDATE office
                SET end_event_id = :event_id
                WHERE corp_num = :corp_num and office_typ_cd = :office_typ_cd and end_event_id is null
                """,
                event_id=event_id,
                corp_num=corp_num,
                office_typ_cd=office_code
            )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errs
            current_app.logger.error('Error updating office table')
            raise err

    @classmethod
    def update_office(cls, cursor, office_info: Dict):
        """Update old office end event id and insert new row into office table.

        office_info.keys() = ['new_event_id', 'corp_num', 'new_delivery_addr_id', 'new_mailing_addr_id', 'office_code']
        """
        cls.end_office(cursor,
                       event_id=office_info['new_event_id'],
                       corp_num=office_info['corp_num'],
                       office_code=office_info['office_code'])
        try:
            cursor.execute(
                """
                INSERT INTO office (corp_num, office_typ_cd, start_event_id, end_event_id, mailing_addr_id,
                    delivery_addr_id)
                VALUES (:corp_num, :office_typ_cd, :start_event_id, null, :mailing_addr_id, :delivery_addr_id)
                """,
                corp_num=office_info['corp_num'],
                office_typ_cd=office_info['office_code'],
                start_event_id=office_info['new_event_id'],
                mailing_addr_id=office_info['new_mailing_addr_id'],
                delivery_addr_id=office_info['new_delivery_addr_id']
            )

        except Exception as err:  # pylint: disable=broad-except; want to catch all errs
            current_app.logger.error('Error inserting into office table')
            raise err

    @classmethod
    def reset_offices_by_events(cls, cursor, event_ids: list):
        """Reset offices to what they were before the given event ids."""
        # get address ids of offices that will be deleted
        addrs_to_delete = Address.get_addresses_by_event(cursor=cursor, event_ids=event_ids, table='office')

        # delete offices created on these events
        delete_from_table_by_event_ids(cursor=cursor, event_ids=event_ids, table='office')

        # delete addresses associated with directors that were deleted
        Address.delete(cursor=cursor, address_ids=addrs_to_delete)

        # reset offices ended on these events
        try:
            cursor.execute(f"""
                UPDATE office
                SET end_event_id = null
                WHERE end_event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error(f'Error in Office: Failed reset ended offices for events {event_ids}')
            raise err
