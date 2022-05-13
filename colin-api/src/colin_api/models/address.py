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
from asyncio.windows_events import NULL
import pycountry
from flask import current_app

from colin_api.exceptions import AddressNotFoundException
from colin_api.resources.db import DB
from colin_api.utils import stringify_list


class Address:  # pylint: disable=too-many-instance-attributes; need all these fields
    """Class to contain all model-like functions such as getting and setting from database."""

    street_address = None
    street_address_additional = None
    address_city = None
    address_region = None
    address_country = None
    postal_code = None
    delivery_instructions = None
    address_id = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self):
        """Return dict version of self."""
        return {
            'streetAddress': self.street_address,
            'streetAddressAdditional': self.street_address_additional,
            'addressCity': self.address_city,
            'addressRegion': self.address_region,
            'addressCountry': self.address_country,
            'postalCode': self.postal_code,
            'deliveryInstructions': self.delivery_instructions,
            'addressId': self.address_id,
            'actions': []
        }

    @classmethod
    def _build_address_obj(cls, address: dict = None):
        # returns address obj given address dict
        if address['addr_line_1'] and address['addr_line_2'] and address['addr_line_3']:
            current_app.logger.error('Expected 2, but got 3 address lines for addr_id: {}'
                                     .format(address['addr_id']))
        if not address['addr_line_1'] and not address['addr_line_2'] and not address['addr_line_3']:
            current_app.logger.error('Expected at least 1 addr_line, but got 0 for addr_id: {}'
                                     .format(address['addr_id']))
        if not address['city'] or not address['province'] or not address['full_desc'] or not address['postal_cd']:
            current_app.logger.error('Missing field in address for addr_id: {}'.format(address['addr_id']))

        # for cases where addresses were input out of order - shift them to lines 1 and 2
        if not address['addr_line_1']:
            if address['addr_line_2']:
                address['addr_line_1'] = address['addr_line_2']
                address['addr_line_2'] = None
        if not address['addr_line_2']:
            if address['addr_line_3']:
                address['addr_line_2'] = address['addr_line_3']
                address['addr_line_3'] = None

        address_obj = Address()
        address_obj.street_address = address['addr_line_1'].strip() if address['addr_line_1'] else ''
        address_obj.street_address_additional = address['addr_line_2'].strip() if address['addr_line_2'] else ''
        address_obj.address_city = address['city'].strip() if address['city'].strip() else ''
        address_obj.address_region = address['province'].strip() if address['province'] else NULL
        address_obj.postal_code = address['postal_cd'].strip() if address['postal_cd'] else ''
        address_obj.address_country = address['full_desc'].strip() if address['full_desc'] else ''
        address_obj.delivery_instructions = address['delivery_instructions'] if address['delivery_instructions'] else ''
        address_obj.address_id = address['addr_id'] if address['addr_id'] else ''

        return address_obj

    @classmethod
    def get_by_address_id(cls, cursor, address_id: str = None):
        """Return single address associated with given addr_id."""
        if not address_id:
            return None

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute("""
                select ADDR_ID, ADDR_LINE_1, ADDR_LINE_2, ADDR_LINE_3, CITY, PROVINCE, COUNTRY_TYPE.FULL_DESC,
                POSTAL_CD, DELIVERY_INSTRUCTIONS
                from ADDRESS
                join COUNTRY_TYPE on ADDRESS.COUNTRY_TYP_CD = COUNTRY_TYPE.COUNTRY_TYP_CD
                where ADDR_ID=:address_id
                """,
                           address_id=address_id
                           )

            address = cursor.fetchone()
            address = dict(zip([x[0].lower() for x in cursor.description], address))
            address_obj = cls._build_address_obj(address)
            return address_obj

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise AddressNotFoundException(address_id=address_id)

    @classmethod
    def create_new_address(cls, cursor, address_info: dict = None, corp_num: str = None):
        """Get new address id and insert address into address table."""
        try:
            if corp_num[:2] == 'CP':
                cursor.execute("""select noncorp_address_seq.NEXTVAL from dual""")
                row = cursor.fetchone()
                addr_id = int(row[0])
            else:
                cursor.execute("""
                    SELECT id_num
                    FROM system_id
                    WHERE id_typ_cd = 'ADD'
                    FOR UPDATE
                """)

                addr_id = int(cursor.fetchone()[0])

                if addr_id:
                    cursor.execute("""
                        UPDATE system_id
                        SET id_num = :new_num
                        WHERE id_typ_cd = 'ADD'
                    """, new_num=addr_id+1)

            country_typ_cd = pycountry.countries.search_fuzzy(address_info.get('addressCountry'))[0].alpha_2
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        try:
            cursor.execute("""
                            INSERT INTO address (addr_id, province, country_typ_cd, postal_cd, addr_line_1, addr_line_2,
                             city, delivery_instructions)
                            VALUES (:addr_id, :province, :country_typ_cd, :postal_cd, :addr_line_1, :addr_line_2, :city,
                                :delivery_instructions)
                            """,
                           addr_id=addr_id,
                           province=address_info['addressRegion'].upper(),
                           country_typ_cd=country_typ_cd,
                           postal_cd=address_info['postalCode'].upper(),
                           addr_line_1=address_info['streetAddress'].upper(),
                           addr_line_2=address_info['streetAddressAdditional'].upper()
                           if 'streetAddressAdditional' in address_info.keys() else '',
                           city=address_info['addressCity'].upper(),
                           delivery_instructions=address_info['deliveryInstructions'].upper()
                           if 'deliveryInstructions' in address_info.keys() else ''
                           )
        except Exception as err:
            current_app.logger.error(f'Error in address: failed to insert new address: {address_info}')
            raise err

        return addr_id

    @classmethod
    def get_addresses_by_event(cls, cursor, event_ids: list, table: str):
        """Get associated addresses given event ids and table."""
        try:
            # table is a value set by the code: not possible to be sql injected from a request
            cursor.execute(f"""
                SELECT delivery_addr_id, mailing_addr_id
                FROM {table}
                WHERE start_event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error(f'Error in Address: Failed to get address ids for events: {event_ids} in table: '
                                     f'{table}')
            raise err

        # make list of associated addresses
        addr_ids = cursor.fetchall()
        addrs_for_return = []
        for row in addr_ids:
            row = dict(zip([x[0].lower() for x in cursor.description], row))
            if row['delivery_addr_id']:
                addrs_for_return.append(row['delivery_addr_id'])
            if row['mailing_addr_id']:
                addrs_for_return.append(row['mailing_addr_id'])
        return addrs_for_return

    @classmethod
    def delete(cls, cursor, address_ids: list = None):
        """Delete given addresses from database."""
        if not address_ids:
            current_app.logger.debug('No addresses give to delete.')
            return
        try:
            # delete addresses from database
            cursor.execute(f"""
                DELETE FROM address
                WHERE addr_id in ({stringify_list(address_ids)})
            """)

            if cursor.rowcount < 1:
                current_app.logger.error('Database not updated.')
                raise Exception
            return
        except Exception as err:
            current_app.logger.error(f'Failed to delete addresses {address_ids}')
            raise err
