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
from __future__ import annotations

from typing import Optional

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
    def _build_address_obj(cls, address: dict) -> Address:
        """Return the parsed address obj given the raw address dict."""
        street_address = ''
        street_address_add = ''
        if address['address_format_type'] in ['BAS', 'ADV']:
            street_elements = [
                address['unit_type'] or '',
                address['unit_no'] or '',
                address['civic_no'] or '',
                address['civic_no_suffix'] or '',
                address['street_name'] or '',
                address['street_type'] or '',
                address['street_direction'] or '']

            street_address = ' '.join([x.strip() for x in street_elements]).strip()

            if address['address_format_type'] == 'ADV':
                street_add_elements = [
                    address['route_service_type'] or '',
                    address['lock_box_no'] or '',
                    address['route_service_no'] or '',
                    address['installation_type'] or '',
                    address['installation_name'] or '']

                street_address += ' '.join([x.strip() for x in street_add_elements])
        else:
            # address format type of 'null' or 'FOR'
            street_address = (address['addr_line_1'] or address['addr_line_2'] or address['addr_line_3'] or '').strip()
            if address['addr_line_1']:
                street_address_add = ' '.join(x.strip() for x in [address['addr_line_2'] or '',
                                                                  address['addr_line_3'] or ''])
            elif address['addr_line_2']:
                street_address_add = (address['addr_line_3'] or '').strip()

        address_obj = Address()
        address_obj.street_address = street_address
        address_obj.street_address_additional = street_address_add
        address_obj.address_city = address['city'].strip() if address['city'] else ''
        address_obj.address_region = address['province'].strip() if address['province'] else None
        address_obj.postal_code = address['postal_cd'].strip() if address['postal_cd'] else ''
        address_obj.address_country = address['full_desc'].strip() if address['full_desc'] else ''
        address_obj.delivery_instructions = address['delivery_instructions'] if address['delivery_instructions'] else ''
        address_obj.address_id = address['addr_id']

        return address_obj

    @classmethod
    def get_by_address_id(cls, cursor, address_id: str = None) -> Optional[Address]:
        """Return single address associated with given addr_id."""
        if not address_id:
            return None

        try:
            if not cursor:
                cursor = DB.connection.cursor()
            cursor.execute("""
                SELECT province, city, postal_cd, addr_line_1, addr_line_2, addr_line_3,
                  unit_type, unit_no, civic_no, civic_no_suffix, street_name, street_type,
                  street_direction, address_format_type, route_service_type, lock_box_no,
                  route_service_no, installation_type, installation_name, addr_id, ct.full_desc, delivery_instructions
                FROM ADDRESS a
                  LEFT JOIN COUNTRY_TYPE ct on a.country_typ_cd = ct.country_typ_cd
                WHERE addr_id=:address_id
                """, address_id=address_id)

            address = cursor.fetchone()
            address = dict(zip([x[0].lower() for x in cursor.description], address))
            return cls._build_address_obj(address)

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise AddressNotFoundException(address_id=address_id)  # pylint: disable=raise-missing-from

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
                    """, new_num=addr_id + 1)

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        try:
            country_typ_cd = pycountry.countries.search_fuzzy(address_info.get('addressCountry'))[0].alpha_2

            province = ''
            province_state_name = (address_info.get('addressRegion') or '').upper()
            if country_typ_cd in ('CA', 'US'):
                province = province_state_name
                province_state_name = ''

            cursor.execute("""
                            INSERT INTO address (addr_id, province, country_typ_cd, postal_cd, addr_line_1, addr_line_2,
                             city, delivery_instructions, province_state_name)
                            VALUES (:addr_id, :province, :country_typ_cd, :postal_cd, :addr_line_1, :addr_line_2, :city,
                                :delivery_instructions, :province_state_name)
                            """,
                           addr_id=addr_id,
                           province=province,
                           country_typ_cd=country_typ_cd,
                           postal_cd=(address_info.get('postalCode') or '').upper(),
                           addr_line_1=(address_info.get('streetAddress') or '').upper(),
                           addr_line_2=(address_info.get('streetAddressAdditional') or '').upper(),
                           city=(address_info.get('addressCity') or '').upper(),
                           delivery_instructions=(address_info.get('deliveryInstructions') or '').upper(),
                           province_state_name=province_state_name
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
                raise Exception  # pylint: disable=broad-exception-raised
            return
        except Exception as err:
            current_app.logger.error(f'Failed to delete addresses {address_ids}')
            raise err
