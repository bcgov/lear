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
from datetime import datetime

from flask import current_app

from colin_api.exceptions import BusinessNotFoundException
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date, convert_to_json_datetime, stringify_list


class Business:
    """Class to contain all model-like functions such as getting and setting from database."""

    business = None

    def __init__(self):
        """Initialize with all values None."""

    def get_corp_num(self):
        """Get corporation number, aka identifier."""
        return self.business['identifier']

    def as_dict(self):
        """Return dict version of self."""
        return {
            'business': self.business
        }

    @classmethod
    def _get_bn_9s(cls, cursor, identifiers: list):
        """Return a dict of idenifiers mapping to their bn_9 numbers."""
        bn_9s = {}
        if not identifiers:
            return bn_9s

        try:
            cursor.execute(f"""
                SELECT corp_num, bn_9
                FROM corporation
                WHERE corp_num in ({stringify_list(identifiers)})
            """)

            for row in cursor.fetchall():
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                if row['bn_9']:
                    bn_9s[f'{row["corp_num"]}'] = row['bn_9']
            return bn_9s

        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed to collect bn_9s for {identifiers}')
            raise err

    @classmethod
    def _get_last_ar_dates_for_reset(cls, cursor, event_info: list, event_ids: list):
        """Get the previous AR/AGM dates."""
        events_by_corp_num = {}
        for info in event_info:
            if info['filing_typ_cd'] != 'OTINC' and \
             (info['corp_num'] not in events_by_corp_num or
              events_by_corp_num[info['corp_num']] > info['event_id']):
                events_by_corp_num[info['corp_num']] = info['event_id']

        dates_by_corp_num = []
        for corp_num in events_by_corp_num:
            cursor.execute(f"""
                SELECT event.corp_num, event.event_timestmp, filing.period_end_dt, filing.agm_date, filing.filing_typ_cd
                FROM event
                JOIN filing on filing.event_id = event.event_id
                WHERE event.event_id not in ({stringify_list(event_ids)}) AND event.corp_num=:corp_num
                ORDER BY event.event_timestmp desc
                """,
                           corp_num=corp_num
                           )

            dates = {'corp_num': corp_num}
            for row in cursor.fetchall():
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                if 'event_date' not in dates or dates['event_date'] < row['event_timestmp']:
                    dates['event_date'] = row['event_timestmp']
                # set ar_date to closest period_end_dt.
                # this is not always the first one that gets returned if 2 were filed on the same day
                if row['period_end_dt'] and ('ar_date' not in dates or dates['ar_date'] < row['period_end_dt']):
                    dates['ar_date'] = row['period_end_dt']
                    dates['ar_filed_date'] = row['event_timestmp']
                # this may be different than ar_date if the last ar had no agm
                if row['agm_date'] and ('agm_date' not in dates or dates['agm_date'] < row['agm_date']):
                    dates['agm_date'] = row['agm_date']
                # if there are no ARs for this coop then use date of incorporation
                if row['filing_typ_cd'] == 'OTINC' and 'agm_date' not in dates:
                    dates['agm_date'] = row['event_timestmp']
                    dates['ar_filed_date'] = row['event_timestmp']

            dates_by_corp_num.append(dates)
        return dates_by_corp_num

    @classmethod
    def find_by_identifier(cls, identifier: str = None, con=None):  # pylint: disable=too-many-statements;
        """Return a Business by identifier."""
        business = None
        if not identifier:
            return None

        try:
            # get record
            if not con:
                con = DB.connection
                con.begin()

            cursor = con.cursor()

            cursor.execute("""
                select corp.CORP_NUM as identifier, CORP_FROZEN_TYP_CD, corp_typ_cd type,
                filing.period_end_dt as last_ar_date, LAST_AR_FILED_DT as last_ar_filed_date, LAST_AGM_DATE,
                corp_op_state.full_desc as state, corp_state.state_typ_cd as corp_state,
                t_name.corp_nme as legal_name,
                t_assumed_name.CORP_NME as assumed_name, RECOGNITION_DTS as founding_date,
                BN_15 as business_number, CAN_JUR_TYP_CD, OTHR_JURIS_DESC
                from CORPORATION corp
                left join CORP_NAME t_name on t_name.corp_num = corp.corp_num and t_name.CORP_NAME_TYP_CD='CO'
                AND t_name.END_EVENT_ID is null
                left join CORP_NAME t_assumed_name on t_assumed_name.corp_num = corp.corp_num
                and t_assumed_name.CORP_NAME_TYP_CD='AS' AND t_assumed_name.END_EVENT_ID is null
                join CORP_STATE on CORP_STATE.corp_num = corp.corp_num and CORP_STATE.end_event_id is null
                join CORP_OP_STATE on CORP_OP_STATE.state_typ_cd = CORP_STATE.state_typ_cd
                left join JURISDICTION on JURISDICTION.corp_num = corp.corp_num
                join event on corp.corp_num = event.corp_num
                left join filing on event.event_id = filing.event_id and filing.filing_typ_cd = 'OTANN'
                where corp_typ_cd in ('CP', 'BC')
                and corp.CORP_NUM=:corp_num
                order by last_ar_date desc nulls last""", corp_num=identifier)
            business = cursor.fetchone()

            if not business:
                raise BusinessNotFoundException(identifier=identifier)

            # add column names to resultset to build out correct json structure and make manipulation below more robust
            # (better than column numbers)
            business = dict(zip([x[0].lower() for x in cursor.description], business))

            # get last ledger date from EVENT table and add to business record
            # note - FILE event type is correct for new filings; CONVOTHER is for events/filings pulled over from COBRS
            # during initial data import for Coops.
            cursor.execute("""
            select max(EVENT_TIMESTMP) as last_ledger_timestamp from EVENT
            where EVENT_TYP_CD in('FILE', 'CONVOTHER') and CORP_NUM = '{}'""".format(identifier))
            last_ledger_timestamp = cursor.fetchone()[0]
            business['last_ledger_timestamp'] = last_ledger_timestamp

            # if this is an XPRO, get correct jurisdiction; otherwise, it's BC
            if business['type'] == 'XCP':
                business['jurisdiction'] = business['can_jur_typ_cd']
                if business['can_jur_typ_cd'] == 'OT':
                    business['jurisdiction'] = business['othr_juris_desc']
            else:
                business['jurisdiction'] = 'BC'

            # set name
            if business['assumed_name']:
                business['legal_name'] = business['assumed_name']

            # set status - In Good Standing if certain criteria met, otherwise use original value
            if business['state'] == 'Active' and \
                    business['last_ar_filed_date'] is not None and \
                    isinstance(business['last_ar_filed_date'], datetime) and \
                    business['last_agm_date'] is not None and isinstance(business['last_agm_date'], datetime):

                business['status'] = business['state']

                if business['last_ar_filed_date'] > business['last_agm_date']:
                    business['status'] = 'In Good Standing'

            else:
                business['status'] = business['state']

            # convert dates and date-times to correct json format and convert to camel case for schema names

            business['foundingDate'] = convert_to_json_datetime(business['founding_date'])
            business['lastAgmDate'] = convert_to_json_date(business['last_agm_date'])
            business['lastArDate'] = convert_to_json_date(business['last_ar_date']) if business['last_ar_date'] \
                else business['lastAgmDate']
            business['lastLedgerTimestamp'] = convert_to_json_datetime(business['last_ledger_timestamp'])

            business['businessNumber'] = business['business_number']
            business['corpState'] = business['corp_state']
            business['legalName'] = business['legal_name']
            business['legalType'] = business['type']

            # remove unnecessary fields (
            del business['can_jur_typ_cd']
            del business['othr_juris_desc']
            del business['assumed_name']
            del business['state']
            del business['business_number']
            del business['corp_frozen_typ_cd']
            del business['corp_state']
            del business['founding_date']
            del business['last_agm_date']
            del business['last_ar_filed_date']
            del business['last_ledger_timestamp']
            del business['legal_name']
            del business['type']
            del business['last_ar_date']

            # add cache_id todo: set to real value
            business['cacheId'] = 0

            # convert to Business object
            business_obj = Business()
            business_obj.business = business
            return business_obj

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def update_corporation(cls, cursor, corp_num: str = None, date: str = None, annual_report: bool = False):
        """Update corporation record.

        :param cursor: oracle cursor
        :param corp_num: (str) corporation number
        :param date: (str) last agm date
        :param annual_report: (bool) whether or not this was an annual report
        """
        try:
            if annual_report:
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
                            LAST_AR_FILED_DT = sysdate,
                            LAST_LEDGER_DT = sysdate
                        WHERE corp_num = :corp_num
                        """,
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
    def update_corp_state(cls, cursor, event_id, corp_num, state='ACT'):
        """Update corporation state.

        End previous corp_state record (end event id) and and create new corp_state record.

        :param cursor: oracle cursor
        :param event_id: (int) event id for corresponding event
        :param corp_num: (str) corporation number
        :param state: (str) state of corporation
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
                VALUES (:corp_num, :event_id, :state)
                """,
                           event_id=event_id,
                           corp_num=corp_num,
                           state=state
                           )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def reset_corporations(cls, cursor, event_info: list, event_ids: list):
        """Reset the corporations to what they were before the given events."""
        if not event_info:
            return

        dates_by_corp_num = cls._get_last_ar_dates_for_reset(cursor=cursor, event_info=event_info, event_ids=event_ids)
        for item in dates_by_corp_num:
            try:

                cursor.execute("""
                    UPDATE corporation
                    SET
                        LAST_AR_FILED_DT = :ar_filed_date,
                        LAST_AGM_DATE = :agm_date,
                        LAST_LEDGER_DT = :event_date
                    WHERE corp_num = :corp_num
                """,
                               agm_date=item['agm_date'] if item['agm_date'] else item['ar_date'],
                               ar_filed_date=item['ar_filed_date'],
                               event_date=item['event_date'],
                               corp_num=item['corp_num']
                               )

            except Exception as err:
                current_app.logger.error(f'Error in Business: Failed to reset corporation for {item["corp_num"]}')
                raise err

    @classmethod
    def reset_corp_states(cls, cursor, event_ids: list):
        """Reset the corp states to what they were before the given events."""
        if not event_ids:
            return

        # delete corp_state rows created on these events
        try:
            cursor.execute(f"""
                DELETE FROM corp_state
                WHERE start_event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed delete corp_state rows for events {event_ids}')
            raise err

        # reset corp_state rows ended on these events
        try:
            cursor.execute(f"""
                UPDATE corp_state
                SET end_event_id = null
                WHERE end_event_id in ({stringify_list(event_ids)})
            """)
        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed reset ended corp_state rows for events {event_ids}')
            raise err

    @classmethod
    def get_next_corp_num(cls, corp_type, con):
        """Retrieve the next available corporation number and advance by one."""
        try:
            cursor = con.cursor()
            cursor.execute("""
                SELECT id_num
                FROM system_id
                WHERE id_typ_cd = :corp_type
                FOR UPDATE
            """, corp_type=corp_type)
            corp_num = cursor.fetchone()

            if corp_num:
                cursor.execute("""
                UPDATE system_id
                SET id_num = :new_num
                WHERE id_typ_cd = :corp_type
            """, new_num=corp_num[0]+1, corp_type=corp_type)

            return corp_num
        except Exception as err:
            current_app.logger.error('Error looking up corp_num')
            raise err

    @classmethod
    def insert_new_business(cls, con, incorporation):
        """Insert a new business from an incorporation filing."""
        try:
            cursor = con.cursor()
            corp_num = incorporation['nameRequest']['nrNumber']
            creation_date = datetime.now()
            legal_type = incorporation['nameRequest']['legalType']
            # Expand query as NR data/ business info becomes more aparent
            cursor.execute("""insert into CORPORATION
            (CORP_NUM, CORP_TYP_CD, RECOGNITION_DTS)
            values (:corp_num, :legal_type, :creation_date)
            """, corp_num=corp_num, legal_type=legal_type, creation_date=creation_date)

            business = {'identifier': corp_num}

            business_obj = Business()
            business_obj.business = business

            return business_obj

        except Exception as err:
            current_app.logger.error('Error inserting business.')
            raise err

    @classmethod
    def create_corp_name(cls, cursor, corp_num, corp_name, event_id):
        """Add record to the CORP NAME table on incorporation."""
        try:
            search_name = ''.join(e for e in corp_name if e.isalnum())
            cursor.execute("""insert into CORP_NAME
            (CORP_NAME_TYP_CD, CORP_NAME_SEQ_NUM, DD_CORP_NUM, END_EVENT_ID,
            CORP_NME, CORP_NUM, START_EVENT_ID, SRCH_NME)
            values ('CO', 0, NULL, NULL, :corp_name, :corp_num, :event_id, :search_name)
            """, corp_name=corp_name, corp_num=corp_num, event_id=event_id, search_name=search_name)

        except Exception as err:
            current_app.logger.error('Error inserting corp name.')
            raise err

    @classmethod
    def create_corp_state(cls, cursor, corp_num, event_id):
        """Add record to the CORP STATE table on incorporation."""
        try:
            cursor.execute("""insert into CORP_STATE
            (CORP_NUM, START_EVENT_ID, STATE_TYP_CD)
            values (:corp_num, :event_id, 'ACT')
            """, corp_num=corp_num, event_id=event_id)

        except Exception as err:
            current_app.logger.error('Error inserting corp state.')
            raise err

    @classmethod
    def create_corp_jurisdiction(cls, cursor, corp_num, event_id):
        """Add record to the JURISDICTION table on incorporation."""
        try:
            cursor.execute("""insert into JURISDICTION
            (CORP_NUM, START_EVENT_ID, STATE_TYP_CD)
            values (:corp_num, :event_id, 'ACT')
            """, corp_num=corp_num, event_id=event_id)

        except Exception as err:
            current_app.logger.error('Error inserting jurisdiction.')
            raise err
