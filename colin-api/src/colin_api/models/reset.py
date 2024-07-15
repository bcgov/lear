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

from colin_api.models.filing import Business, Filing, Office, Party, ShareObject
from colin_api.resources.db import DB
from colin_api.utils import stringify_list


class Reset:
    """Class to contain all model-like functions for resetting filings."""

    # dicts containing data
    start_date = '2019-08-10'
    end_date = '9999-12-31'
    identifiers = []
    filing_types = []

    def __init__(self):
        """Initialize with all default values."""

    def as_dict(self):
        """Return dict camel case version of self."""
        return {
            'reset_info': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'identifiers': self.identifiers,
                'filing_types': self.filing_types
            }
        }

    def get_filings_for_reset(self):
        """Return event/filing info for all filings getting reset."""
        # build base query string
        query_string = """
            select event.event_id, event.corp_num, filing_typ_cd
            from event
            join filing on filing.event_id = event.event_id
            left join filing_user on event.event_id = filing_user.event_id
            where filing_user.user_id in ('COOPER', 'BCOMPS')
            AND event.event_timestmp>=TO_DATE(:start_date, 'yyyy-mm-dd')
            AND event.event_timestmp<=TO_DATE(:end_date, 'yyyy-mm-dd')
        """

        if self.identifiers:
            query_string += f' AND event.corp_num in ({stringify_list(self.identifiers)})'

        if self.filing_types:
            query_string += f' AND filing.filing_typ_cd in ({stringify_list(self.filing_types)})'

        # order by most most recent
        query_string += '  ORDER BY event.event_timestmp desc'

        try:
            cursor = DB.connection.cursor()
            cursor.execute(
                query_string,
                start_date=self.start_date,
                end_date=self.end_date,
            )
            reset_raw_info = cursor.fetchall()
            reset_list = []
            for row in reset_raw_info:
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                reset_list.append(row)

            return reset_list

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            current_app.logger.error(f'error getting filing/event info for reset for: {self.as_dict()}')
            raise err

    @classmethod
    def _delete_events_and_filings(cls, cursor, event_ids: list):
        """Delete rows in the filing and event tables with the given event ids."""
        try:
            cursor.execute(f"""
                DELETE FROM filing
                WHERE event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to delete from filing table.')
            raise err

        try:
            cursor.execute(f"""
                DELETE FROM event
                WHERE event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to delete from event table.')
            raise err

    @classmethod
    def _delete_ledger_text(cls, cursor, event_ids: list):
        """Delete rows in the ledger_text table with the given event ids."""
        try:
            cursor.execute(f"""
                    DELETE FROM ledger_text
                    WHERE event_id in ({stringify_list(event_ids)})
                """)
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to delete from ledger_text table.')
            raise err

    @classmethod
    def _delete_filing_user(cls, cursor, event_ids: list):
        """Delete rows in the filing_user table with the given event ids."""
        try:
            cursor.execute(f"""
                    DELETE FROM filing_user
                    WHERE event_id in ({stringify_list(event_ids)})
                """)
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to delete from filing_user table.')
            raise err

    @classmethod
    def _delete_corp_name(cls, cursor, event_ids: list):
        events_str = ', '.join(str(x) for x in event_ids)
        if events_str:
            try:
                cursor.execute(f"""
                        DELETE FROM corp_name
                        WHERE start_event_id in ({events_str})
                    """)
            except Exception as err:
                current_app.logger.error('Error in Reset: failed to delete from corp_name table.')
                raise err

    @classmethod
    def _delete_new_corps(cls, cursor, corp_nums: list):
        if corp_nums:
            try:
                cursor.execute(f"""
                        DELETE FROM corporation
                        WHERE corp_num in ({stringify_list(corp_nums)})
                    """)
            except Exception as err:
                current_app.logger.error('Error in Reset: failed to delete from corp_name table.')
                raise err

    @classmethod
    def _delete_corp_state(cls, cursor, corp_nums: list):
        if corp_nums:
            try:
                cursor.execute(f"""
                        DELETE FROM corp_state
                        WHERE corp_num in ({stringify_list(corp_nums)})
                    """)
            except Exception as err:
                current_app.logger.error('Error in Reset: failed to delete from corp_name table.')
                raise err

    @classmethod
    def _delete_messages(cls, cursor, event_ids: list):
        """Delete rows mars_message_outbound table with the given event ids."""
        try:
            cursor.execute(f"""
                    DELETE FROM MRAS_MESSAGE_OUTBOUND
                    WHERE stg_id in ({stringify_list(event_ids)})
                """)
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to delete from mras message outbound table.')
            raise err

    @classmethod
    def _get_incorporations_by_event(cls, cursor, event_ids: list):
        """Find all corporation entries associated with an incorporation."""
        new_corps = {}
        try:
            events = stringify_list(event_ids)
            events = events.replace("'", '')
            cursor.execute(f"""SELECT A.CORP_NUM, B.EVENT_ID FROM
            EVENT A JOIN FILING B ON A.EVENT_ID = B.EVENT_ID
            WHERE B.EVENT_ID IN({events}) AND B.FILING_TYP_CD in ('OTINC', 'BEINC')""")
            for row in cursor.fetchall():
                new_corps[row[0]] = row[1]
            return new_corps
        except Exception as err:
            current_app.logger.error('Error in Reset: failed to retrieve incorporation filing.')
            raise err

    @classmethod
    def reset_filings(cls, start_date: str = None, end_date: str = None, identifiers: list = None,
                      filing_types: list = None):
        """Reset changes made by COOPER for given identifiers/dates/filing types."""
        # initialize reset object
        reset_obj = Reset()
        if start_date:
            reset_obj.start_date = start_date
        if end_date:
            reset_obj.start_date = end_date
        if identifiers:
            reset_obj.identifiers = identifiers
        if filing_types:
            reset_obj.filing_types = filing_types

        # place into lists that can be reset together
        events = []
        annual_report_events = []
        events_info = []

        for filing_info in reset_obj.get_filings_for_reset():
            events.append(filing_info['event_id'])
            events_info.append(filing_info)
            if filing_info['filing_typ_cd'] in Filing.FILING_TYPES['annualReport']['type_code_list']:
                annual_report_events.append(filing_info['event_id'])

        try:
            if events:
                # setup db connection
                con = DB.connection
                con.begin()
                cursor = con.cursor()

                # reset data in oracle for events
                new_corps = cls._get_incorporations_by_event(cursor, events)
                Party.reset_dirs_by_events(cursor=cursor, event_ids=events)
                Office.reset_offices_by_events(cursor=cursor, event_ids=events)
                Business.reset_corp_states(cursor=cursor, event_ids=annual_report_events)
                Business.reset_corporations(cursor=cursor, event_info=events_info, event_ids=events)
                ShareObject.delete_shares(cursor, events)
                cls._delete_filing_user(cursor=cursor, event_ids=events)
                cls._delete_ledger_text(cursor=cursor, event_ids=events)
                cls._delete_corp_name(cursor=cursor, event_ids=list(new_corps.values()))
                cls._delete_corp_state(cursor=cursor, corp_nums=list(new_corps.keys()))
                cls._delete_events_and_filings(cursor=cursor, event_ids=events)
                cls._delete_new_corps(cursor=cursor, corp_nums=list(new_corps.keys()))
                con.commit()
                return
        except Exception as err:
            current_app.logger.error('Error in reset_filings: failed to reset filings.'
                                     ' Rolling back any partial changes.')
            if con:
                con.rollback()
            raise err

    @classmethod
    def reset_filings_by_event(cls, event_ids: list = []):
        """Reset changes made for given event ids."""
        # initialize reset object
        reset_obj = Reset()

        # place into lists that can be reset together
        annual_report_events = []
        events_info = []

        for filing_info in reset_obj.get_filings_for_reset():
            if filing_info['event_id'] in event_ids:
                events_info.append(filing_info)
                if filing_info['filing_typ_cd'] in Filing.FILING_TYPES['annualReport']['type_code_list']:
                    annual_report_events.append(filing_info['event_id'])

        try:
            if event_ids:
                # setup db connection
                con = DB.connection
                con.begin()
                cursor = con.cursor()

                # reset data in oracle for events
                # The commented out events do not seem to happen for AR so they are commented out.
                new_corps = cls._get_incorporations_by_event(cursor, event_ids)
                Party.reset_dirs_by_events(cursor=cursor, event_ids=event_ids)
                Office.reset_offices_by_events(cursor=cursor, event_ids=event_ids)
                Business.reset_corp_states(cursor=cursor, event_ids=event_ids)
                Business.reset_corporations(cursor=cursor, event_info=events_info, event_ids=event_ids)
                ShareObject.delete_shares(cursor, event_ids)
                cls._delete_messages(cursor=cursor, event_ids=event_ids)
                cls._delete_filing_user(cursor=cursor, event_ids=event_ids)
                cls._delete_ledger_text(cursor=cursor, event_ids=event_ids)
                cls._delete_corp_name(cursor=cursor, event_ids=list(new_corps.values()))
                cls._delete_corp_state(cursor=cursor, corp_nums=list(new_corps.keys()))
                cls._delete_events_and_filings(cursor=cursor, event_ids=event_ids)
                cls._delete_new_corps(cursor=cursor, corp_nums=list(new_corps.keys()))
                con.commit()
                return
        except Exception as err:
            current_app.logger.error('Error in reset_filings_by_event: failed to reset filings.'
                                     ' Rolling back any partial changes.')
            if con:
                con.rollback()
            raise err
