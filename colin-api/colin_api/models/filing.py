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

import datetime

from flask import current_app
from registry_schemas import convert_to_json_date

from colin_api.exceptions import FilingNotFoundException, InvalidFilingTypeException
from colin_api.models import Business
from colin_api.resources.db import db


class Filing():
    """Class to contain all model-like functions such as getting and setting from database."""

    # dicts containing data
    business = None
    header = None
    body = None
    filing_type = None

    def __init__(self):
        pass

    def get_corp_num(self):
        """Get corporation num, aka identifier."""
        return self.business.business['identifier']

    def get_last_name(self):
        """Get last name; currently is whole name."""
        return self.body['certified_by']

    def get_email(self):
        """Get email address."""
        return self.body['email']

    def as_dict(self):
        """Return dict of object that can be json serialized and fits schema requirements."""
        return {
            "filing": {
                "header": self.header,
                self.filing_type: self.body,
                "business_info": self.business.business
            }
        }

    @classmethod
    def find_filing(cls, business: Business = None, filing_type: str = None, year: int = None):
        """Return a Filing."""
        if not business or not filing_type:
            return None

        try:
            print(business)
            identifier = business.get_corp_num()

            # set filing type code from filing_type (string)
            if filing_type == 'annual_report':
                filing_type_code = 'OTANN'
                filing_obj = cls.find_ar(business, identifier, year)

            elif filing_type == 'registered_office_address':
                filing_obj = cls.find_reg_off_addr(business, identifier, year)
                print(filing_obj)
            else:
                # default value
                filing_type_code = 'FILE'

            return filing_obj

        except FilingNotFoundException as err:
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def add_filing(cls, filing):
        """Add new filing to COLIN tables.

        :param filing: Filing dict.
        :returns (int): the filing ID of the new filing.
        """
        try:
            corp_num = filing.get_corp_num()

            # get db connection and start a session, in case we need to roll back
            con = db.connection
            con.begin()

            cursor = con.cursor()

            print('1 ', filing)
            # create new event record, return event ID
            event_id = cls._get_event_id(cursor, corp_num, 'FILE')
            print('4 ', event_id)
            # create new filing user
            cls._add_filing_user(cursor, event_id, filing)

            if filing.filing_type == 'annual_report':
                date = filing.body['annual_general_meeting_date']
                filing_type_cd = 'OTANN'

            elif filing.filing_type == 'registered_office_address':
                date = filing.business.business['last_agm_date']
                filing_type_cd = 'OTADD'
                print('date ', date)
                cls._add_ledger_text(cursor, event_id, 'Change to the Registered Office, effective on {} as filed with'
                                                       ' {} Annual Report'.format(date, date[:4]))
                delivery_addr_id = cls._get_address_id(cursor, event_id, corp_num, 'RG', filing.body['business_office']['legal_address']['delivery_address'])
                mailing_addr_id = cls._get_address_id(cursor, event_id, corp_num, 'RG', filing.body['business_office']['legal_address']['mailing_address'])
                cls._update_office(cursor, event_id, corp_num, delivery_addr_id, mailing_addr_id, 'RG')

            else:
                raise InvalidFilingTypeException(identifier=filing.business.business['identifier'],
                                                 filing_type=filing.filing_type)

            # create new filing
            cls._add_filing(cursor, event_id, filing, date, filing_type_cd)

            # update corporation record
            cls._update_corporation(cursor, corp_num, filing.body['annual_general_meeting_date'])

            # update corp_state TO ACT (active) if it is in good standing. From CRUD:
            # - the current corp_state != 'ACT' and,
            # - they just filed the last outstanding ARs
            if filing.business.business['corp_state'] != 'ACT':
                agm_year = int(date[:4])
                last_year = datetime.datetime.now().year - 1
                if agm_year >= last_year:
                    cls._update_corp_state(cursor, event_id, corp_num, state='ACT')

            # success! commit the db changes
            con.commit()

        except Exception as err:
            # something went wrong, roll it all back
            current_app.logger.error(err.with_traceback(None))
            if con:
                con.rollback()

            raise err

    @classmethod
    def _get_event_id(cls, cursor, corp_num, event_type='FILE'):
        """Get next event ID for filing.

        :param cursor: oracle cursor
        :return: (int) event ID
        """
        cursor.execute("""select noncorp_event_seq.NEXTVAL from dual""")
        row = cursor.fetchone()
        event_id = int(row[0])
        try:
            cursor.execute("""
            INSERT INTO event (event_id, corp_num, event_typ_cd, event_timestmp, trigger_dts)
              VALUES (:event_id, :corp_num, :event_type, sysdate, NULL)
            """,
                           event_id=event_id,
                           corp_num=corp_num,
                           event_type=event_type
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        return event_id

    @classmethod
    def _add_filing(cls, cursor, event_id, filing, date, filing_type_code='FILE'):
        """Add record to FILING.

        Note: Period End Date and AGM Date are both the AGM Date value for Co-ops.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        :param date: (str) period_end_date
        :param filing_type_code: (str) filing type code
        """
        if not filing_type_code:
            raise FilingNotFoundException(filing.business.business['identifier'], filing.filing_type)
        try:
            print('8 ', filing_type_code)
            if filing_type_code is 'OTANN':
                cursor.execute("""
                INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt, agm_date)
                  VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:period_end_date, 'YYYY-mm-dd'),
                  TO_DATE(:agm_date, 'YYYY-mm-dd'))
                """,
                               event_id=event_id,
                               filing_type_code=filing_type_code,
                               period_end_date=date,
                               agm_date=date
                               )
            elif filing_type_code is 'OTADD':
                cursor.execute("""
                INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt)
                  VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:period_end_date, 'YYYY-mm-dd'))
                """,
                               event_id=event_id,
                               filing_type_code=filing_type_code,
                               period_end_date=date,
                               )
        except Exception as err:
            print('filing')
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _add_filing_user(cls, cursor, event_id, filing):
        """Add to the FILING_USER table.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        """
        try:
            cursor.execute("""
            INSERT INTO filing_user (event_id, user_id, last_nme, first_nme, middle_nme, email_addr, party_typ_cd,
            role_typ_cd)
              VALUES (:event_id, NULL, :last_name, NULL, NULL, :email_address, NULL, NULL)
            """,
                           event_id=event_id,
                           last_name=filing.get_last_name(),
                           email_address=filing.get_email()
                           )
        except Exception as err:
            print('filing_user')
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _update_corporation(cls, cursor, corp_num, date):
        """Update corporation record.

        :param cursor: oracle cursor
        :param corp_num: (str) corporation number
        """
        try:
            cursor.execute("""
            UPDATE corporation
            SET
                LAST_AR_FILED_DT = sysdate,
                LAST_AGM_DATE = TO_DATE(:agm_date, 'YYYY-mm-dd'),
                LAST_LEDGER_DT = sysdate
            WHERE corp_num = :corp_num
            """,
                           agm_date=date,
                           corp_num=corp_num
                           )

        except Exception as err:
            print('corporation')
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _update_corp_state(cls, cursor, event_id, corp_num, state='ACT'):
        """Update corporation state.

        End previous corp_state record (end event id) and and create new corp_state record.

        :param cursor: oracle cursor
        :param filing: (obj) Filing data object
        """
        try:
            cursor.execute("""
            UPDATE corp_state
            SET end_event_id = :event_id
            WHERE corp_num = :corp_num and end_event_id is NULL
            """,
                           event_id=event_id,
                           corp_num=corp_num
                           )

        except Exception as err:
            print('corp_state1')
            current_app.logger.error(err.with_traceback(None))
            raise err
        try:
            cursor.execute("""
            INSERT INTO corp_state (corp_num, start_event_id, state_typ_cd)
              VALUES (:corp_num, :event_id, :state
              )
            """,
                           event_id=event_id,
                           corp_num=corp_num,
                           state=state
                           )

        except Exception as err:
            print('corp_state2')
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _add_ledger_text(cls, cursor, event_id, text):
        try:
            cursor.execute("""
            INSERT INTO ledger_text (event_id, ledger_text_dts, notation)
              VALUES (:event_id, sysdate, :notation)
            """,
                           event_id=event_id,
                           notation=text
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _get_address_id(cls, cursor, event_id, corp_num, office_typ_cd, address_info):

        cursor.execute("""select noncorp_address_seq.NEXTVAL from dual""")
        row = cursor.fetchone()
        addr_id = int(row[0])
        try:
            cursor.execute("""
                    select country_typ_cd from country_type where full_desc=:country
                  """,
                           country=address_info['country'].upper()
                           )
            country_typ_cd = cursor.fetchone()
            print('country_typ_cd: ', country_typ_cd)
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        try:
            cursor.execute("""
                    INSERT INTO address (addr_id, province, country_typ_cd, postal_cd, addr_line_1, addr_line_2, city,
                     corp_num, office_typ_cd, start_event_id, end_event_id, mailing_addr_id, delivery_addr_id)
                     VALUES (:addr_id, :province, :country_typ_cd, :postal_cd, :addr_line_1, :addr_line_2, :city,
                      :corp_num, :office_typ_cd, :start_event_id, null, )
                    """,
                           addr_id=addr_id,
                           province=address_info['province'].upper(),
                           country_typ_cd=country_typ_cd[0],
                           postal_cd=address_info['postal_code'].upper(),
                           addr_line_1=address_info['street_address_line1'].upper(),
                           addr_line_2=address_info['street_address_line2'].upper(),
                           city=address_info['city'].upper(),
                           corp_num=corp_num,
                           office_typ_cd=office_typ_cd,
                           start_event_id=event_id
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        return addr_id

    @classmethod
    def _update_office(cls, cursor, event_id, corp_num, delivery_addr_id, mailing_addr_id, office_typ_cd):

        try:
            cursor.execute("""
                    UPDATE office
                    SET end_event_id = :event_id
                    WHERE corp_num = :corp_num and office_typ_cd = :office_typ_cd and end_event_id is null
                    """,
                           event_id=event_id,
                           corp_num=corp_num,
                           office_typ_cd=office_typ_cd
                           )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        try:
            cursor.execute("""
                    INSERT INTO office (corp_num, office_typ_cd, start_event_id, end_event_id, mailing_addr_id,
                     delivery_addr_id)
                    VALUES (:corp_num, :office_typ_cd, :start_event_id, null, :mailing_addr_id, :delivery_addr_id)
                    """,
                           corp_num=corp_num,
                           office_typ_cd=office_typ_cd,
                           start_event_id=event_id,
                           mailing_addr_id=mailing_addr_id,
                           delivery_addr_id=delivery_addr_id
                           )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def find_ar(cls, business: Business = None, identifier: str = None, year: int = None):

        # build base querystring
        querystring = (
            "select event.EVENT_TIMESTMP, EFFECTIVE_DT, AGM_DATE, PERIOD_END_DT, NOTATION, "
            "FIRST_NME, LAST_NME, MIDDLE_NME, EMAIL_ADDR "
            "from EVENT "
            "join FILING on EVENT.EVENT_ID = FILING.EVENT_ID "
            "left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID "
            "left join LEDGER_TEXT on EVENT.EVENT_ID = LEDGER_TEXT.EVENT_ID "
            "where CORP_NUM='{}' and FILING_TYP_CD='{}' ".format(identifier, 'OTANN')
        )

        # condition by year on period end date - for coops, this is same as AGM date; for corps, this is financial
        # year end date.
        if year:
            querystring += ' AND extract(year from PERIOD_END_DT) = {}'.format(year)

        querystring += ' order by EVENT_TIMESTMP desc'

        # get record
        cursor = db.connection.cursor()
        cursor.execute(querystring)
        filing = cursor.fetchone()

        if not filing:
            raise FilingNotFoundException(identifier=identifier, filing_type='annual_report')

        # add column names to resultset to build out correct json structure and make manipulation below more robust
        # (better than column numbers)
        filing = dict(zip([x[0].lower() for x in cursor.description], filing))

        # if there is no AGM date in period_end_dt, check agm_date and effective date
        try:
            agm_date = next(item for item in [
                filing['period_end_dt'], filing['agm_date'], filing['effective_dt']
            ] if item is not None)
        except StopIteration:
            agm_date = None

        # build filing user name from first, middle, last name
        filing_user_name = ' '.join(filter(None, [filing['first_nme'], filing['middle_nme'], filing['last_nme']]))
        if not filing_user_name:
            filing_user_name = 'Unavailable'

        # if email is blank, set as empty tring
        if not filing['email_addr']:
            filing['email_addr'] = 'missing@missing.com'

        # convert dates and date-times to correct json format
        filing['event_timestmp'] = convert_to_json_date(filing['event_timestmp'])
        agm_date = convert_to_json_date(agm_date)

        filing_obj = Filing()
        filing_obj.business = business
        filing_obj.header = {
            'date': filing['event_timestmp'],
            'name': 'annual_report'
        }
        filing_obj.body = {
            'annual_general_meeting_date': agm_date,
            'certified_by': filing_user_name,
            'email': filing['email_addr']
        }
        filing_obj.filing_type = 'annual_report'

        return filing_obj

    @classmethod
    def find_reg_off_addr(cls, business: Business = None, identifier: str = None, year: int = None):
        # build base querystring
        # todo: check full_desc in country_type table matches with canada post api for foreign countries
        querystring = (
            "select ADDR_LINE_1, ADDR_LINE_2, ADDR_LINE_3, CITY, PROVINCE, COUNTRY_TYPE.FULL_DESC, POSTAL_CD, "
            "DELIVERY_INSTRUCTIONS, EVENT.EVENT_TIMESTMP "
            "from ADDRESS "
            "join OFFICE on ADDRESS.ADDR_ID = OFFICE.{} "
            "join COUNTRY_TYPE on ADDRESS.COUNTRY_TYP_CD = COUNTRY_TYPE.COUNTRY_TYP_CD "
            "join EVENT on OFFICE.START_EVENT_ID = EVENT.EVENT_ID "
            "where OFFICE.END_EVENT_ID IS NULL and OFFICE.CORP_NUM='{}' and OFFICE.OFFICE_TYP_CD='{}' "
        )
        querystring_delivery = (
            querystring.format('DELIVERY_ADDR_ID', identifier, 'RG')
        )
        querystring_mailing = (
            querystring.format('MAILING_ADDR_ID', identifier, 'RG')
        )

        # get record
        cursor = db.connection.cursor()
        cursor.execute(querystring_delivery)
        delivery_address = cursor.fetchone()
        test = cursor.fetchone()
        if test:
            current_app.logger.error('More than 1 delivery address returned - update oracle sql in find_reg_off_addr')
        cursor.execute(querystring_mailing)
        mailing_address = cursor.fetchone()
        test = cursor.fetchone()
        if test:
            current_app.logger.error('More than 1 mailing address returned - update oracle sql in find_reg_off_addr')

        if not delivery_address:
            raise FilingNotFoundException(identifier=identifier, filing_type='registered_office_address')

        print(delivery_address)
        print(mailing_address)

        # add column names to result set to build out correct json structure and make manipulation below more robust
        # (better than column numbers)
        delivery_address = dict(zip([x[0].lower() for x in cursor.description], delivery_address))
        mailing_address = dict(zip([x[0].lower() for x in cursor.description], mailing_address))

        print(delivery_address)
        print(mailing_address)

        # todo: check all fields for data - may be different for data outside of coops
        # expecting data-fix for all bad data in address table for coops: this will catch if anything was missed
        if delivery_address['addr_line_1'] and delivery_address['addr_line_2'] and delivery_address['addr_line_3']:
            current_app.logger.error('Expected 2, but got 3 delivery address lines for: {}'.format(identifier))
        if not delivery_address['addr_line_1'] and not delivery_address['addr_line_2'] and not delivery_address['addr_line_3']:
            current_app.logger.error('Expected at least 1 delivery addr_line, but got 0 for: {}'.format(identifier))
        if not delivery_address['city'] or not delivery_address['province'] or not delivery_address['full_desc'] \
                or not delivery_address['postal_cd']:
            current_app.logger.error('Missing field in delivery address for: {}'.format(identifier))

        if mailing_address['addr_line_1'] and mailing_address['addr_line_2'] and mailing_address['addr_line_3']:
            current_app.logger.error('Expected 2, but 3 mailing address lines returned for: {}'.format(identifier))
        if not mailing_address['city'] or not mailing_address['province'] or not mailing_address['full_desc'] \
                or not delivery_address['postal_cd']:
            current_app.logger.error('Missing field in mailing address for: {}'.format(identifier))

        # for cases where delivery addresses were input out of order - shift them to lines 1 and 2
        if not delivery_address['addr_line_1']:
            if delivery_address['addr_line_2']:
                delivery_address['addr_line_1'] = delivery_address['addr_line_2']
                delivery_address['addr_line_2'] = None
        if not delivery_address['addr_line_2']:
            if delivery_address['addr_line_3']:
                delivery_address['addr_line_2'] = delivery_address['addr_line_3']
                delivery_address['addr_line_3'] = None

        delivery_address['country'] = delivery_address['full_desc']
        mailing_address['country'] = mailing_address['full_desc']

        filing_obj = Filing()
        filing_obj.business = business
        filing_obj.header = {
            'date': delivery_address['event_timestmp'],
            'name': 'registered_office_address'
        }
        filing_obj.body = {
            "business_office": {
                "legal_address": {
                    "shipping_address": [
                        {
                            "street_address_line1": delivery_address['addr_line_1'],
                            "street_address_line2": delivery_address['addr_line_2'],
                            "city": delivery_address['city'],
                            "province": delivery_address['province'],
                            "country": delivery_address['country'],
                            "postal_code": delivery_address['postal_cd']
                        },
                        {
                            "type": 'registered_office'
                        }
                    ]
                },
                "mailing_address": {
                    "street_address_line1": mailing_address['addr_line_1'],
                    "street_address_line2": mailing_address['addr_line_2'],
                    "city": mailing_address['city'],
                    "province": mailing_address['province'],
                    "country": mailing_address['country'],
                    "postal_code": mailing_address['postal_cd']
                }
            }
        },
        filing_obj.filing_type = 'registered_office_address'

        return filing_obj
