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
from colin_api.models import Address
from colin_api.resources.db import db


class Office:

    delivery_address = None
    mailing_address = None
    event_id = None

    def __init__(self):
        pass

    def as_dict(self):
        return {
            'deliveryAddress': self.delivery_address,
            'mailingAddress': self.mailing_address
        }

    @classmethod
    def get_current(cls, identifier: str = None):
        """return current registered office address"""
        if not identifier:
            return None

        querystring = (
            """
            select start_event_id, mailing_addr_id, delivery_addr_id
            from office
            where corp_num=:identifier and end_event_id is null and office_typ_cd='RG'
            """
        )

        try:
            cursor = db.connection.cursor()
            cursor.execute(querystring, identifier=identifier)

            office_info = cursor.fetchone()
            test_second_office = cursor.fetchone()
            if test_second_office:
                current_app.logger.error('got more than 1 current registered office address for {}'.format(identifier))

            office_info = dict(zip([x[0].lower() for x in cursor.description], office_info))

            office_obj = Office()
            office_obj.event_id = office_info['start_event_id']
            office_obj.delivery_address = Address.get_by_address_id(office_info['delivery_addr_id']).as_dict()
            office_obj.mailing_address = Address.get_by_address_id(office_info['mailing_addr_id']).as_dict()

            return office_obj

        except Exception as err:
            current_app.logger.error('error getting office for corp: {}'.format(identifier))
            raise err

    @classmethod
    def get_by_event(cls, event_id: str = None):
        """return current registered office address"""
        if not event_id:
            return None

        querystring = (
            """
            select start_event_id, mailing_addr_id, delivery_addr_id
            from office
            where start_event_id=:event_id and office_typ_cd='RG'
            """
        )

        try:
            cursor = db.connection.cursor()
            cursor.execute(querystring, event_id=event_id)

            office_info = cursor.fetchone()
            office_info = dict(zip([x[0].lower() for x in cursor.description], office_info))

            office_obj = Office()
            office_obj.event_id = office_info['start_event_id']
            office_obj.delivery_address = Address.get_by_address_id(office_info['delivery_addr_id']).as_dict()
            office_obj.mailing_address = Address.get_by_address_id(office_info['mailing_addr_id']).as_dict()

            return office_obj

        except Exception as err:
            current_app.logger.error('error getting office from event : {}'.format(event_id))
            raise err
