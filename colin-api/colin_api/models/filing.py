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

from colin_api.exceptions import FilingNotFoundException, InvalidFilingTypeException
from colin_api.models import Address, Business, Director, Office
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date


class Filing:
    """Class to contain all model-like functions such as getting and setting from database."""

    # dicts containing data
    business = None
    header = None
    body = None
    filing_type = None
    event_id = None

    def __init__(self):
        """Initialize with all values None."""

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
            'filing': {
                'header': self.header,
                self.filing_type: self.body,
                'business': self.business.business,
                'eventId': self.event_id
            }
        }

    @classmethod
    def find_filing(cls, business: Business = None, event_id: str = None, filing_type: str = None, year: int = None):
        """Return a Filing."""
        if not business or not filing_type:
            return None

        try:
            identifier = business.get_corp_num()

            if filing_type == 'annualReport':
                filing_obj = cls.find_ar(identifier=identifier, event_id=event_id, year=year)

            elif filing_type == 'changeOfAddress':
                filing_obj = cls.find_change_of_addr(identifier=identifier, event_id=event_id, year=year)

            elif filing_type == 'changeOfDirectors':
                filing_obj = cls.find_change_of_dir(identifier=identifier, event_id=event_id, year=year)

            else:
                raise InvalidFilingTypeException(filing_type=filing_type)

            filing_obj.business = business

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
    def add_filing(cls, filing):  # pylint: disable=too-many-locals; filing needs a lot of vars to build
        """Add new filing to COLIN tables.

        :param filing: Filing dict.
        :returns (int): the filing ID of the new filing.
        """
        try:
            corp_num = filing.get_corp_num()

            # get db connection and start a session, in case we need to roll back
            con = DB.connection
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
                day = int(last_agm_date[-2:]) + 1
                try:
                    date = str(datetime.datetime.strptime(last_agm_date[:-2] + ('0' + str(day))[1:], '%Y-%m-%d'))[:10]
                except ValueError:
                    try:
                        day = '-01'
                        month = int(last_agm_date[5:7]) + 1
                        date = str(datetime.datetime.strptime(last_agm_date[:5] + ('0' + str(month))[1:] + day,
                                                              '%Y-%m-%d')
                                   )[:10]
                    except ValueError:
                        mm_dd = '-01-01'
                        yyyy = int(last_agm_date[:4]) + 1
                        date = str(datetime.datetime.strptime(str(yyyy) + mm_dd, '%Y-%m-%d'))[:10]
                filing_type_cd = 'OTADD'

                # create new filing
                cls._add_filing(cursor, event_id, filing, date, filing_type_cd)

                # create new addresses for delivery + mailing, return address ids
                delivery_addr_id = Address.create_new_address(cursor, filing.body['deliveryAddress'])
                mailing_addr_id = Address.create_new_address(cursor, filing.body['mailingAddress'])

                # update office table to include new addresses
                Office.update_office(cursor, event_id, corp_num, delivery_addr_id, mailing_addr_id, 'RG')

                # update corporation record
                cls._update_corporation(cursor, corp_num, None)

                # create new ledger text for address change
                cls._add_ledger_text(cursor, event_id, 'Change to the Registered Office, effective on {} as filed with'
                                                       ' {} Annual Report'.format(date, date[:4]))

            else:
                raise InvalidFilingTypeException(filing_type=filing.filing_type)

            # success! commit the db changes
            con.commit()
            return event_id

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
    def _add_filing(cls, cursor, event_id, filing, date,  # pylint: disable=too-many-arguments; need all these args
                    filing_type_code='FILE'):
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
            if filing_type_code == 'OTANN':
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
            elif filing_type_code == 'OTADD':
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
    def _find_filing_event_info(cls,  # pylint: disable=too-many-arguments; needed to work for all filing types
                                identifier: str = None, event_id: str = None, filing_type_cd1: str = None,
                                filing_type_cd2: str = 'empty', year: int = None):

        # build base querystring
        querystring = ("""
            select event.event_id, event_timestmp, first_nme, middle_nme, last_nme, email_addr, period_end_dt, agm_date,
            effective_dt
            from event
            join filing on filing.event_id = event.event_id
            left join filing_user on event.event_id = filing_user.event_id
            where (filing_typ_cd=:filing_type_cd1 or filing_typ_cd=:filing_type_cd2)
            """)

        if identifier:
            querystring += ' AND event.corp_num=:identifier'

        if event_id:
            querystring += ' AND event.event_id=:event_id'

        if year:
            querystring += ' AND extract(year from PERIOD_END_DT)=:year'

        querystring += ' order by EVENT_TIMESTMP desc'

        try:
            cursor = DB.connection.cursor()
            if event_id:
                if year:
                    cursor.execute(querystring, event_id=event_id, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2, year=year)
                else:
                    cursor.execute(querystring, event_id=event_id, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2)
            else:
                if year:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2, year=year)
                else:
                    cursor.execute(querystring, identifier=identifier, filing_type_cd1=filing_type_cd1,
                                   filing_type_cd2=filing_type_cd2)

            event_info = cursor.fetchone()

            if not event_info:
                raise FilingNotFoundException(identifier=identifier, filing_type='1: {} 2: {}'.format(
                    filing_type_cd1, filing_type_cd2))

            event_info = dict(zip([x[0].lower() for x in cursor.description], event_info))

            # build filing user name from first, middle, last name
            filing_user_name = ' '.join(
                filter(None, [event_info['first_nme'], event_info['middle_nme'], event_info['last_nme']]))
            filing_email = event_info['email_addr']

            if not filing_user_name:
                filing_user_name = 'N/A'

            # if email is blank, set as empty tring
            if not filing_email:
                filing_email = 'xxxx@xxxx.xxx'

            event_info['certifiedBy'] = filing_user_name
            event_info['email'] = filing_email

            return event_info

        except Exception as err:
            current_app.logger.error('error getting filing event id for {}'.format(identifier))
            raise err

    @classmethod
    def find_ar(cls, identifier: str = None, event_id: str = None, year: int = None):
        """Return annual report filing."""
        if event_id:
            filing_event_info = cls._find_filing_event_info(event_id=event_id, filing_type_cd1='OTANN', year=year)
        else:
            filing_event_info = cls._find_filing_event_info(identifier=identifier, filing_type_cd1='OTANN', year=year)

        if not filing_event_info:
            raise FilingNotFoundException(identifier=identifier, filing_type='annualReport')

        # if there is no AGM date in period_end_dt, check agm_date and effective date
        try:
            agm_date = next(item for item in [
                filing_event_info['period_end_dt'], filing_event_info['agm_date'], filing_event_info['effective_dt']
            ] if item is not None)
        except StopIteration:
            agm_date = None

        # convert dates and date-times to correct json format
        filing_event_info['event_timestmp'] = convert_to_json_date(filing_event_info['event_timestmp'])
        agm_date = convert_to_json_date(agm_date)

        filing_obj = Filing()

        filing_obj.header = {
            'date': filing_event_info['event_timestmp'],
            'name': 'annualReport'
        }
        filing_obj.body = {
            'annualGeneralMeetingDate': agm_date,
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email']
        }
        filing_obj.filing_type = 'annualReport'
        filing_obj.event_id = filing_event_info['event_id']

        return filing_obj

    @classmethod
    def find_change_of_addr(cls, identifier: str = None, event_id: str = None,
                            year: int = None):  # pylint: disable=unused-argument; will use year later
        """Return change of address filing."""
        if event_id:
            filing_event_info = cls._find_filing_event_info(event_id=event_id, filing_type_cd1='OTADD',
                                                            filing_type_cd2='OTARG')
        else:
            filing_event_info = cls._find_filing_event_info(identifier=identifier, filing_type_cd1='OTADD',
                                                            filing_type_cd2='OTARG')

        registered_office_obj = Office.get_by_event(filing_event_info['event_id'])

        if not registered_office_obj:
            raise FilingNotFoundException(identifier=identifier, filing_type='change_of_address')

        filing_obj = Filing()
        filing_obj.header = {
            'date': convert_to_json_date(filing_event_info['event_timestmp']),
            'name': 'changeOfAddress'
        }
        filing_obj.body = {
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email'],
            **registered_office_obj.as_dict()
        }
        filing_obj.filing_type = 'changeOfAddress'
        filing_obj.event_id = filing_event_info['event_id']

        return filing_obj

    @classmethod
    def find_change_of_dir(cls, identifier: str = None, event_id: str = None,
                           year: int = None):  # pylint: disable=unused-argument; will use year later
        """Return most current directors in filing format."""
        filing_obj = Filing()

        if event_id:
            filing_event_info = cls._find_filing_event_info(event_id=event_id, filing_type_cd1='OTCDR',
                                                            filing_type_cd2='OTADR')
        else:
            filing_event_info = cls._find_filing_event_info(identifier=identifier, filing_type_cd1='OTCDR',
                                                            filing_type_cd2='OTADR')

        director_objs = Director.get_by_event(filing_event_info['event_id'])
        if len(director_objs) < 3:
            current_app.logger.error('Less than 3 directors for {}'.format(identifier))

        filing_obj.header = {
            'date': convert_to_json_date(filing_event_info['event_timestmp']),
            'name': 'changeOfDirectors'
        }

        filing_obj.body = {
            'certifiedBy': filing_event_info['certifiedBy'],
            'email': filing_event_info['email'],
            'directors': [x.as_dict() for x in director_objs]
        }
        filing_obj.filing_type = 'changeOfDirector'
        filing_obj.event_id = filing_event_info['event_id']

        return filing_obj
