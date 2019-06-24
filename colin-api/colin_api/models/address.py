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

from colin_api.exceptions import AddressNotFoundException
from colin_api.resources.db import DB


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
            'streetAddress_additional': self.street_address_additional,
            'addressCity': self.address_city,
            'addressRegion': self.address_region,
            'addressCountry': self.address_country,
            'postalCode': self.postal_code,
            'deliveryInstructions': self.delivery_instructions,
            'addressId': self.address_id
        }

    @classmethod
    def get_by_address_id(cls, address_id: str = None):
        """Return single address associated with given addr_id."""
        if not address_id:
            return None

        try:
            cursor = DB.connection.cursor()
            cursor.execute("""
                select ADDR_ID, ADDR_LINE_1, ADDR_LINE_2, ADDR_LINE_3, CITY, PROVINCE, COUNTRY_TYPE.FULL_DESC,
                POSTAL_CD, DELIVERY_INSTRUCTIONS
                from ADDRESS
                join COUNTRY_TYPE on ADDRESS.COUNTRY_TYP_CD = COUNTRY_TYPE.COUNTRY_TYP_CD
                where ADDR_ID=:address_id
                """, address_id=address_id)

            address = cursor.fetchone()
            address = dict(zip([x[0].lower() for x in cursor.description], address))
            address_obj = cls._build_address_obj(address)
            return address_obj

        except Exception as err:
            current_app.logger.error('error getting address with id: {}'.format(address_id))
            raise err

    @classmethod
    def find_current_by_identifier(cls, identifier: str = None,  # pylint: disable=too-many-locals; need all these vars
                                   address_grp: str = None, typ_cd: str = None):
        """Return most current addresses by corpnum and address group (office, corp_party, etc.)."""
        # build base querystring
        # todo: check full_desc in country_type table matches with canada post api for foreign countries
        querystring = ("""
            select ADDR_ID, ADDR_LINE_1, ADDR_LINE_2, ADDR_LINE_3, CITY, PROVINCE, COUNTRY_TYPE.FULL_DESC, POSTAL_CD,
            DELIVERY_INSTRUCTIONS, EVENT.EVENT_TIMESTMP, FILING_USER.FIRST_NME, FILING_USER.LAST_NME,
            FILING_USER.MIDDLE_NME, FILING_USER.EMAIL_ADDR
            from ADDRESS
            join {address_grp} on ADDRESS.ADDR_ID = {address_grp}.{addr_id_typ}
            join COUNTRY_TYPE on ADDRESS.COUNTRY_TYP_CD = COUNTRY_TYPE.COUNTRY_TYP_CD
            join EVENT on {address_grp}.START_EVENT_ID = EVENT.EVENT_ID
            left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID
            where {address_grp}.END_EVENT_ID IS NULL and {address_grp}.CORP_NUM=:corp_num
            """)

        if typ_cd == 'RG':
            querystring += "and {address_grp}.OFFICE_TYP_CD='{typ_cd}'".format(address_grp=address_grp, typ_cd=typ_cd)

        elif typ_cd == 'DIR':
            if typ_cd == 'RG':
                querystring += "and {address_grp}.PARTY_TYP_CD='{typ_cd}'".format(address_grp=address_grp,
                                                                                  typ_cd=typ_cd)

        querystring_delivery = querystring.format(address_grp=address_grp, addr_id_typ='DELIVERY_ADDR_ID')
        querystring_mailing = querystring.format(address_grp=address_grp, addr_id_typ='MAILING_ADDR_ID')
        try:
            # get record
            cursor = DB.connection.cursor()
            cursor.execute(querystring_delivery, corp_num=identifier)
            delivery_addresses = cursor.fetchall()

            cursor.execute(querystring_mailing, corp_num=identifier)
            mailing_addresses = cursor.fetchall()

        except Exception as err:
            current_app.logger.error('error getting address info for {}'.format(identifier))
            raise err

        if not delivery_addresses:
            raise AddressNotFoundException(identifier=identifier, address_type='deliveryAddress')
        if not mailing_addresses:
            raise AddressNotFoundException(identifier=identifier, address_type='mailingAddress')

        if len(delivery_addresses) != len(mailing_addresses):
            current_app.logger.error('Should have the same number of delivery + mailing addresses: {corp_num}, {type}'
                                     .format(corp_num=identifier, type=address_grp))
            raise AddressNotFoundException(
                identifier=identifier,
                address_type='mailingAddress'
                if len(mailing_addresses) < len(delivery_addresses) else 'deliveryAddress')

        addresses = []
        for delivery, mailing in zip(delivery_addresses, mailing_addresses):
            addresses.append({'deliveryAddress': dict(zip([x[0].lower() for x in cursor.description], delivery)),
                              'mailingAddress': dict(zip([x[0].lower() for x in cursor.description], mailing))})

        # todo: check all fields for data - may be different for data outside of coops
        # expecting data-fix for all bad data in address table for coops: this will catch if anything was missed
        address_objs = []
        for address_pair in addresses:
            delivery_address = cls._build_address_obj(address_pair['deliveryAddress'])
            mailing_address = cls._build_address_obj(address_pair['mailingAddress'])
            address_objs.append((delivery_address.as_dict(), mailing_address.as_dict()))

        return address_objs

    @classmethod
    def create_new_address(cls, cursor, address_info):
        """Get new address id and insert address into address table."""
        try:
            cursor.execute("""select noncorp_address_seq.NEXTVAL from dual""")
            row = cursor.fetchone()
            addr_id = int(row[0])
            cursor.execute("""
                            select country_typ_cd from country_type where full_desc=:country
                          """, country=address_info['addressCountry'].upper())
            country_typ_cd = (cursor.fetchone())[0]
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
            current_app.logger.error(err.with_traceback(None))
            raise err

        return addr_id

    @classmethod
    def _build_address_obj(cls, address):
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
        address_obj.address_region = address['province'].strip() if address['province'] else ''
        address_obj.postal_code = address['postal_cd'].strip() if address['postal_cd'] else ''
        address_obj.address_country = address['full_desc'].strip() if address['full_desc'] else ''
        address_obj.delivery_instructions = address['delivery_instructions'] if address['delivery_instructions'] else ''
        address_obj.address_id = address['addr_id'] if address['addr_id'] else ''

        return address_obj
