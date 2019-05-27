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
from colin_api.utils import convert_to_json_date

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
        return self.body['certifiedBy']

    def get_email(self):
        """Get email address."""
        return self.body['email']

    def as_dict(self):
        """Return dict of object that can be json serialized and fits schema requirements."""
        return {
            "filing": {
                "header": self.header,
                self.filing_type: self.body,
                "business": self.business.business
            }
        }

    @classmethod
    def find_filing(cls, business: Business = None, filing_type: str = None, year: int = None):
        """Return a Filing."""
        if not business or not filing_type:
            return None

        try:
            identifier = business.get_corp_num()

            # set filing type code from filing_type (string)
            if filing_type == 'annualReport':
                filing_type_code = 'OTANN'
                filing_obj = cls.find_ar(business, identifier, year)

            elif filing_type == 'changeOfAddress':
                filing_obj = cls.find_change_of_addr(business, identifier, year)
            else:
                # default value
                filing_type_code = 'FILE'
                raise InvalidFilingTypeException

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

            # create new event record, return event ID
            event_id = cls._get_event_id(cursor, corp_num, 'FILE')

            # create new filing user
            cls._add_filing_user(cursor, event_id, filing)

            if filing.filing_type == 'annualReport':
                date = filing.body['annualGeneralMeetingDate']
                filing_type_cd = 'OTANN'

                # create new filing
                cls._add_filing(cursor, event_id, filing, date, filing_type_cd)

                # update corporation record
                cls._update_corporation(cursor, corp_num, date)

                # update corp_state TO ACT (active) if it is in good standing. From CRUD:
                # - the current corp_state != 'ACT' and,
                # - they just filed the last outstanding ARs
                if filing.business.business['corpState'] != 'ACT':
                    agm_year = int(date[:4])
                    last_year = datetime.datetime.now().year - 1
                    if agm_year >= last_year:
                        cls._update_corp_state(cursor, event_id, corp_num, state='ACT')

            elif filing.filing_type == 'changeOfAddress':

                # set date to last agm date + 1
                last_agm_date = filing.business.business['lastAgmDate']
                dd = int(last_agm_date[-2:]) + 1
                try:
                    date = str(datetime.datetime.strptime(last_agm_date[:-2] + ('0' + str(dd))[1:], "%Y-%m-%d"))[:10]
                except ValueError as err:
                    try:
                        dd = '-01'
                        mm = int(last_agm_date[5:7]) + 1
                        date = str(datetime.datetime.strptime(last_agm_date[:5] + ('0' + str(mm))[1:] + dd, "%Y-%m-%d"))[:10]
                    except ValueError as err:
                        mm_dd = '-01-01'
                        yyyy = int(last_agm_date[:4]) + 1
                        date = str(datetime.datetime.strptime(str(yyyy) + mm_dd, "%Y-%m-%d"))[:10]
                filing_type_cd = 'OTADD'

                # create new filing
                cls._add_filing(cursor, event_id, filing, date, filing_type_cd)

                # create new addresses for delivery + mailing, return address ids
                delivery_addr_id = cls._get_address_id(cursor, filing.body['deliveryAddress'])
                mailing_addr_id = cls._get_address_id(cursor, filing.body['mailingAddress'])

                # update office table to include new addresses
                cls._update_office(cursor, event_id, corp_num, delivery_addr_id, mailing_addr_id, 'RG')

                # update corporation record
                cls._update_corporation(cursor, corp_num, None)

                # create new ledger text for address change
                cls._add_ledger_text(cursor, event_id, 'Change to the Registered Office, effective on {} as filed with'
                                                       ' {} Annual Report'.format(date, date[:4]))

            else:
                raise InvalidFilingTypeException(identifier=filing.business.business['identifier'],
                                                 filing_type=filing.filing_type)

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
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _update_corporation(cls, cursor, corp_num, date):
        """Update corporation record.

        :param cursor: oracle cursor
        :param corp_num: (str) corporation number
        """
        try:
            if date:
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

            else:
                cursor.execute("""
                                UPDATE corporation
                                SET
                                    LAST_LEDGER_DT = sysdate
                                WHERE corp_num = :corp_num
                                """,
                               corp_num=corp_num
                               )

        except Exception as err:
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
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _add_ledger_text(cls, cursor, event_id, text):
        try:
            cursor.execute("""
            INSERT INTO ledger_text (event_id, ledger_text_dts, notation, dd_event_id)
              VALUES (:event_id, sysdate, :notation, :dd_event_id)
            """,
                           event_id=event_id,
                           notation=text,
                           dd_event_id=event_id
                           )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def _get_address_id(cls, cursor, address_info):

        cursor.execute("""select noncorp_address_seq.NEXTVAL from dual""")
        row = cursor.fetchone()
        addr_id = int(row[0])
        try:
            cursor.execute("""
                    select country_typ_cd from country_type where full_desc=:country
                  """,
                           country=address_info['addressCountry'].upper()
                           )
            country_typ_cd = (cursor.fetchone())[0]
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

        try:
            cursor.execute("""
                    INSERT INTO address (addr_id, province, country_typ_cd, postal_cd, addr_line_1, addr_line_2, city,
                        delivery_instructions)
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
            """
            select event.EVENT_TIMESTMP, EFFECTIVE_DT, AGM_DATE, PERIOD_END_DT, NOTATION,
            FIRST_NME, LAST_NME, MIDDLE_NME, EMAIL_ADDR
            from EVENT
            join FILING on EVENT.EVENT_ID = FILING.EVENT_ID 
            left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID 
            left join LEDGER_TEXT on EVENT.EVENT_ID = LEDGER_TEXT.EVENT_ID 
            where CORP_NUM=:identifier and FILING_TYP_CD=:filing_typ_cd  
            """
        )

        # condition by year on period end date - for coops, this is same as AGM date; for corps, this is financial
        # year end date.
        if year:
            querystring += ' AND extract(year from PERIOD_END_DT) = {}'.format(year)

        querystring += ' order by EVENT_TIMESTMP desc '

        # get record
        cursor = db.connection.cursor()
        cursor.execute(querystring, identifier=identifier, filing_typ_cd='OTANN')
        filing = cursor.fetchone()

        if not filing:
            raise FilingNotFoundException(identifier=identifier, filing_type='annualReport')

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
            'name': 'annualReport'
        }
        filing_obj.body = {
            'annualGeneralMeetingDate': agm_date,
            'certifiedBy': filing_user_name,
            'email': filing['email_addr']
        }
        filing_obj.filing_type = 'annualReport'

        return filing_obj

    @classmethod
    def find_change_of_addr(cls, business: Business = None, identifier: str = None, year: int = None):
        # build base querystring
        # todo: check full_desc in country_type table matches with canada post api for foreign countries
        querystring = (
            """
            select ADDR_LINE_1, ADDR_LINE_2, ADDR_LINE_3, CITY, PROVINCE, COUNTRY_TYPE.FULL_DESC, POSTAL_CD,
            DELIVERY_INSTRUCTIONS, EVENT.EVENT_TIMESTMP, FILING_USER.FIRST_NME, FILING_USER.LAST_NME,
            FILING_USER.MIDDLE_NME, FILING_USER.EMAIL_ADDR
            from ADDRESS
            join OFFICE on ADDRESS.ADDR_ID = OFFICE.{addr_id_typ}
            join COUNTRY_TYPE on ADDRESS.COUNTRY_TYP_CD = COUNTRY_TYPE.COUNTRY_TYP_CD
            join EVENT on OFFICE.START_EVENT_ID = EVENT.EVENT_ID
            left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID
            where OFFICE.END_EVENT_ID IS NULL and OFFICE.CORP_NUM=:corp_num and OFFICE.OFFICE_TYP_CD=:office_typ_cd
            """
        )
        querystring_delivery = (
            querystring.format(addr_id_typ='DELIVERY_ADDR_ID')
        )
        querystring_mailing = (
            querystring.format(addr_id_typ='MAILING_ADDR_ID')
        )

        # get record
        cursor = db.connection.cursor()
        cursor.execute(querystring_delivery, corp_num=identifier, office_typ_cd='RG')
        delivery_address = cursor.fetchone()
        test = cursor.fetchone()
        if test:
            current_app.logger.error('More than 1 delivery address returned - update oracle sql in find_reg_off_addr')

        cursor.execute(querystring_mailing, corp_num=identifier, office_typ_cd='RG')
        mailing_address = cursor.fetchone()
        test = cursor.fetchone()
        if test:
            current_app.logger.error('More than 1 mailing address returned - update oracle sql in find_reg_off_addr')

        if not delivery_address:
            raise FilingNotFoundException(identifier=identifier, filing_type='change_of_address')

        # add column names to result set to build out correct json structure and make manipulation below more robust
        # (better than column numbers)
        delivery_address = dict(zip([x[0].lower() for x in cursor.description], delivery_address))
        mailing_address = dict(zip([x[0].lower() for x in cursor.description], mailing_address))

        # build filing user name from first, middle, last name
        filing_user_name = ' '.join(filter(None, [delivery_address['first_nme'], delivery_address['middle_nme'],
                                                  delivery_address['last_nme']]))
        if not filing_user_name:
            filing_user_name = 'N/A'

        # if email is blank, set as N/A
        if not delivery_address['email_addr']:
            delivery_address['email_addr'] = 'N/A'

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

        delivery_address['event_timestmp'] = convert_to_json_date(delivery_address['event_timestmp'])
        mailing_address['event_timestmp'] = convert_to_json_date(mailing_address['event_timestmp'])

        filing_obj = Filing()
        filing_obj.business = business
        filing_obj.header = {
            'date': delivery_address['event_timestmp'],
            'name': 'changeOfAddress'
        }
        filing_obj.body = {
            "certifiedBy": filing_user_name,
            "email": delivery_address['email_addr'],
            "deliveryAddress": {
                "streetAddress": delivery_address['addr_line_1'],
                "streetAddressAdditional": delivery_address['addr_line_2'] if delivery_address['addr_line_2'] else '',
                "addressCity": delivery_address['city'],
                "addressRegion": delivery_address['province'],
                "addressCountry": delivery_address['country'],
                "postalCode": delivery_address['postal_cd'],
                "deliveryInstructions": delivery_address['delivery_instructions']
                if delivery_address['delivery_instructions'] else ''
            },
            "mailingAddress": {
                "streetAddress": mailing_address['addr_line_1'],
                "streetAddressAdditional": mailing_address['addr_line_2'] if mailing_address['addr_line_2'] else '',
                "addressCity": mailing_address['city'],
                "addressRegion": mailing_address['province'],
                "addressCountry": mailing_address['country'],
                "postalCode": mailing_address['postal_cd'],
                "deliveryInstructions": mailing_address['delivery_instructions']
                if mailing_address['delivery_instructions'] else ''
            }
        }
        filing_obj.filing_type = 'changeOfAddress'

        return filing_obj
