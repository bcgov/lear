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

from colin_api.exceptions import FilingNotFoundException
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

            identifier = business.get_corp_num()

            # set filing type code from filing_type (string)
            if filing_type == 'annual_report':
                filing_type_code = 'OTANN'
            else:
                # default value
                filing_type_code = 'FILE'

            # build base querystring
            querystring = (
                "select event.EVENT_TIMESTMP, EFFECTIVE_DT, AGM_DATE, PERIOD_END_DT, NOTATION, "
                "FIRST_NME, LAST_NME, MIDDLE_NME, EMAIL_ADDR "
                "from EVENT "
                "join FILING on EVENT.EVENT_ID = FILING.EVENT_ID "
                "left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID "
                "left join LEDGER_TEXT on EVENT.EVENT_ID = LEDGER_TEXT.EVENT_ID "
                "where CORP_NUM='{}' and FILING_TYP_CD='{}' ".format(identifier, filing_type_code)
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
                raise FilingNotFoundException(identifier=identifier, filing_type=filing_type)

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
                    'name': filing_type
                }
            filing_obj.body = {
                    'annual_general_meeting_date': agm_date,
                    'certified_by': filing_user_name,
                    'email': filing['email_addr']
                }
            filing_obj.filing_type = filing_type

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

            # get db connection and start a session, in case we need to roll back
            con = db.connection
            con.begin()

            cursor = con.cursor()

            # create new event record, return event ID
            event_id = cls._get_event_id(cursor, filing, 'FILE')

            # create new filing
            cls._add_filing(cursor, event_id, filing, 'OTANN')

            # create new filing user
            cls._add_filing_user(cursor, event_id, filing)

            # update corporation record
            cls._update_corporation(cursor, filing)

            # update corp_state TO ACT (active) if it is in good standing. From CRUD:
            # - the current corp_state != 'ACT' and,
            # - they just filed the last outstanding ARs
            if filing.business.business['corp_state'] != 'ACT':
                agm_year = int(filing.body['annual_general_meeting_date'][:4])
                last_year = datetime.datetime.now().year - 1
                if agm_year >= last_year:
                    cls._update_corp_state(cursor, event_id, filing, state='ACT')

            # success! commit the db changes
            con.commit()

        except Exception as err:
            # something went wrong, roll it all back
            current_app.logger.error(err.with_traceback(None))
            if con:
                con.rollback()

            raise err

    @classmethod
    def _get_event_id(cls, cursor, filing, event_type='FILE'):
        """Get next event ID for filing.

        :param cursor: oracle cursor
        :return: (int) event ID
        """
        cursor.execute("""select noncorp_event_seq.NEXTVAL from dual""")
        row = cursor.fetchone()

        event_id = int(row[0])

        cursor.execute("""
        INSERT INTO event (event_id, corp_num, event_typ_cd, event_timestmp, trigger_dts)
          VALUES (:event_id, :corp_num, :event_type, sysdate, NULL)
        """,
                       event_id=event_id,
                       corp_num=filing.get_corp_num(),
                       event_type=event_type
                       )

        return event_id

    @classmethod
    def _add_filing(cls, cursor, event_id, filing, filing_type_code='OTANN'):
        """Add record to FILING.

        Note: Period End Date and AGM Date are both the AGM Date value for Co-ops.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        :param filing_type_code: (str) filing type code, defaults to Other Annual Report ("OTANN")
        """
        cursor.execute("""
        INSERT INTO filing (event_id, filing_typ_cd, effective_dt, period_end_dt, agm_date)
          VALUES (:event_id, :filing_type_code, sysdate, TO_DATE(:agm_date, 'YYYY-mm-dd'),
          TO_DATE(:agm_date, 'YYYY-mm-dd'))
        """,
                       event_id=event_id,
                       filing_type_code=filing_type_code,
                       agm_date=filing.body['annual_general_meeting_date']
                       )

    @classmethod
    def _add_filing_user(cls, cursor, event_id, filing):
        """Add to the FILING_USER table.

        :param cursor: oracle cursor
        :param event_id: (int) event_id for all events for this transaction
        :param filing: (obj) Filing data object
        """
        cursor.execute("""
        INSERT INTO filing_user (event_id, user_id, last_nme, first_nme, middle_nme, email_addr, party_typ_cd,
        role_typ_cd)
          VALUES (:event_id, NULL, :last_name, NULL, NULL, :email_address, NULL, NULL)
        """,
                       event_id=event_id,
                       last_name=filing.get_last_name(),
                       email_address=filing.get_email()
                       )

    @classmethod
    def _update_corporation(cls, cursor, filing):
        """Update corporation record.

        :param cursor: oracle cursor
        :param filing: (obj) Filing data object
        """
        cursor.execute("""
        UPDATE corporation
        SET
            LAST_AR_FILED_DT = sysdate,
            LAST_AGM_DATE = TO_DATE(:agm_date, 'YYYY-mm-dd'),
            LAST_LEDGER_DT = sysdate
        WHERE corp_num = :corp_num
        """,
                       agm_date=filing.body['annual_general_meeting_date'],
                       corp_num=filing.get_corp_num()
                       )

    @classmethod
    def _update_corp_state(cls, cursor, event_id, filing, state='ACT'):
        """Update corporation state.

        End previous corp_state record (end event id) and and create new corp_state record.

        :param cursor: oracle cursor
        :param filing: (obj) Filing data object
        """
        cursor.execute("""
        UPDATE corp_state
        SET end_event_id = :event_id
        WHERE corp_num = :corp_num and end_event_id is NULL
        """,
                       event_id=event_id,
                       corp_num=filing.get_corp_num()
                       )

        cursor.execute("""
        INSERT INTO corp_state (corp_num, start_event_id, state_typ_cd)
          VALUES (:corp_num, :event_id, :state
          )
        """,
                       event_id=event_id,
                       corp_num=filing.get_corp_num(),
                       state=state
                       )
