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

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from datedelta import datedelta
from flask import current_app

from colin_api.exceptions import BusinessNotFoundException
from colin_api.models.corp_name import CorpName
from colin_api.resources.db import DB
from colin_api.utils import convert_to_json_date, convert_to_json_datetime, convert_to_pacific_time, stringify_list


class Business:  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Class to contain all model-like functions for the corporation and related tables."""

    class TypeCodes(Enum):
        """Render an Enum of the Corporation Type Codes."""

        EXTRA_PRO_A = 'A'
        COOP = 'CP'
        BCOMP = 'BEN'
        BC_COMP = 'BC'
        ULC_COMP = 'ULC'
        CCC_COMP = 'CC'
        BCOMP_CONTINUE_IN = 'CBEN'
        CONTINUE_IN = 'C'
        CCC_CONTINUE_IN = 'CCC'
        ULC_CONTINUE_IN = 'CUL'

    class CorpFrozenTypes(Enum):
        """Render an Enum of the Corporation Frozen Type Codes.

        The following frozen states are used for:
        COMPANY_FROZEN is when the Registrar has frozen a company
        SELF_SERVED_FROZEN is a legacy code used to freeze a company and now is deprecated.
        """

        COMPANY_FROZEN = 'C'
        SELF_SERVED_FROZEN = 'S'  # Deprecated

    class CorpStateTypes(Enum):
        """Render an Enum of the CorpState Type Codes."""

        ACTIVE = 'ACT'
        ADMINISTRATIVE_DISSOLUTION = 'HDA'
        AMALGAMATED = 'HAM'
        AMALGAMATE_OUT = 'HAO'
        CONTINUE_IN = 'HCI'
        CONTINUE_OUT = 'HCO'
        INVOLUNTARY_DISSOLUTION_NO_AR = 'HDF'  # this corp state is also used for Put back off
        INVOLUNTARY_DISSOLUTION_NO_TR = 'HDT'
        LIMITED_RESTORATION = 'LRS'
        RESTORATION_EXPIRATION = 'EXR'
        VOLUNTARY_DISSOLUTION = 'HDV'
    CORPS = [TypeCodes.BCOMP.value,
             TypeCodes.BC_COMP.value,
             TypeCodes.ULC_COMP.value,
             TypeCodes.CCC_COMP.value,
             TypeCodes.BCOMP_CONTINUE_IN.value,
             TypeCodes.CONTINUE_IN.value,
             TypeCodes.ULC_CONTINUE_IN.value,
             TypeCodes.CCC_CONTINUE_IN.value]

    NUMBERED_CORP_NAME_SUFFIX = {
        TypeCodes.BCOMP.value: 'B.C. LTD.',
        TypeCodes.BC_COMP.value: 'B.C. LTD.',
        TypeCodes.ULC_COMP.value: 'B.C. UNLIMITED LIABILITY COMPANY',
        TypeCodes.CCC_COMP.value: 'B.C. COMMUNITY CONTRIBUTION COMPANY LTD.',
    }

    # CORPS Continuation In has the same suffix
    NUMBERED_CORP_NAME_SUFFIX[TypeCodes.BCOMP_CONTINUE_IN.value] = NUMBERED_CORP_NAME_SUFFIX[TypeCodes.BCOMP.value]
    NUMBERED_CORP_NAME_SUFFIX[TypeCodes.CONTINUE_IN.value] = NUMBERED_CORP_NAME_SUFFIX[TypeCodes.BC_COMP.value]
    NUMBERED_CORP_NAME_SUFFIX[TypeCodes.ULC_CONTINUE_IN.value] = NUMBERED_CORP_NAME_SUFFIX[TypeCodes.ULC_COMP.value]
    NUMBERED_CORP_NAME_SUFFIX[TypeCodes.CCC_CONTINUE_IN.value] = NUMBERED_CORP_NAME_SUFFIX[TypeCodes.CCC_COMP.value]

    business_number = None
    corp_name = None
    corp_num = None
    corp_state = None
    corp_type = None
    corp_state_class = None
    email = None
    founding_date = None
    good_standing = None
    jurisdiction = None
    home_recogn_dt = None
    home_juris_num = None
    home_company_nme = None
    last_agm_date = None
    last_ar_date = None
    last_ledger_timestamp = None
    status = None
    admin_freeze = None

    def __init__(self):
        """Initialize with all values None."""

    def as_dict(self) -> Dict:
        """Return dict version of self."""
        return {
            'business': {
                'businessNumber': self.business_number,
                'corpState': self.corp_state,
                'corpStateClass': self.corp_state_class,
                'email': self.email,
                'foundingDate': self.founding_date,
                'goodStanding': self.good_standing,
                'identifier': self.corp_num,
                'jurisdiction': self.jurisdiction,
                'homeRecognitionDate': self.home_recogn_dt,
                'homeJurisdictionNumber': self.home_juris_num,
                'homeCompanyName': self.home_company_nme,
                'lastAgmDate': self.last_agm_date,
                'lastArDate': self.last_ar_date,
                'lastLedgerTimestamp': self.last_ledger_timestamp,
                'legalName': self.corp_name,
                'legalType': self.corp_type,
                'status': self.status,
                'adminFreeze': self.admin_freeze
            }
        }

    def as_slim_dict(self) -> Dict:
        """Return slim dict version of self."""
        return {
            'business': {
                'businessNumber': self.business_number,
                'corpState': self.corp_state,
                'corpStateClass': self.corp_state_class,
                'foundingDate': self.founding_date,
                'identifier': self.corp_num,
                'jurisdiction': self.jurisdiction,
                'homeRecognitionDate': self.home_recogn_dt,
                'homeJurisdictionNumber': self.home_juris_num,
                'homeCompanyName': self.home_company_nme,
                'legalName': self.corp_name,
                'legalType': self.corp_type,
                'status': self.status,
                'adminFreeze': self.admin_freeze
            }
        }

    @classmethod
    def get_colin_identifier(cls, lear_identifier, legal_type):
        """Convert identifier from lear to colin."""
        if legal_type in [
            cls.TypeCodes.BCOMP.value,
            cls.TypeCodes.BC_COMP.value,
            cls.TypeCodes.ULC_COMP.value,
            cls.TypeCodes.CCC_COMP.value
        ] and lear_identifier.startswith('BC'):
            return lear_identifier[2:]

        return lear_identifier

    @classmethod
    def _get_bn_15s(cls, cursor, identifiers: List) -> Dict:
        """Return a dict of idenifiers mapping to their bn_15 numbers."""
        bn_15s = {}
        if not identifiers:
            return bn_15s

        try:
            cursor.execute(
                f"""
                SELECT corp_num, bn_15
                FROM corporation
                WHERE corp_num in ({stringify_list(identifiers)})
                """
            )

            for row in cursor.fetchall():
                row = dict(zip([x[0].lower() for x in cursor.description], row))
                if row['bn_15']:
                    if row['corp_num'].isdecimal():  # valid only for BC
                        bn_15s[f'BC{row["corp_num"]}'] = row['bn_15']
                    else:
                        bn_15s[row['corp_num']] = row['bn_15']
            return bn_15s

        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed to collect bn_9s for {identifiers}')
            raise err

    @classmethod
    def _get_last_ar_dates_for_reset(cls, cursor, event_info: List, event_ids: List) -> List:
        """Get the previous AR/AGM dates."""
        events_by_corp_num = {}
        for info in event_info:
            if info['filing_typ_cd'] not in ['OTINC', 'BEINC'] and \
                (info['corp_num'] not in events_by_corp_num or
                 events_by_corp_num[info['corp_num']] > info['event_id']):
                events_by_corp_num[info['corp_num']] = info['event_id']

        dates_by_corp_num = []
        for corp_num in events_by_corp_num:
            cursor.execute(
                f"""
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
                if row['filing_typ_cd'] in ['OTINC', 'BEINC'] and 'agm_date' not in dates:
                    dates['agm_date'] = row['event_timestmp']
                    dates['ar_filed_date'] = row['event_timestmp']

            dates_by_corp_num.append(dates)
        return dates_by_corp_num

    @classmethod
    def find_by_identifier(cls,  # pylint: disable=too-many-statements
                           identifier: str,
                           corp_types: List = None,
                           con=None) -> Business:
        """Return a Business by identifier."""
        business = None
        try:
            # get record
            if not con:
                con = DB.connection
                # con.begin()

            corp_type_condition = ''
            if corp_types:
                corp_type_condition = f'corp.corp_typ_cd in ({stringify_list(corp_types)}) and '

            cursor = con.cursor()
            cursor.execute(
                f"""
                select corp.corp_num, corp.corp_typ_cd,
                    CASE WHEN corp.corp_frozen_typ_cd is null THEN 'False'
                         ELSE 'True'
                    END AS admin_freeze,
                    recognition_dts, bn_15, can_jur_typ_cd, othr_juris_desc,
                    home_recogn_dt, home_juris_num, home_company_nme,
                    filing.period_end_dt, last_agm_date, corp_op_state.full_desc as state, admin_email,
                    corp_state.state_typ_cd as corp_state, corp_op_state.op_state_typ_cd as corp_state_class,
                    corp.last_ar_filed_dt, corp.transition_dt, ct.corp_class
                from CORPORATION corp
                    join CORP_STATE on CORP_STATE.corp_num = corp.corp_num and CORP_STATE.end_event_id is null
                    join CORP_OP_STATE on CORP_OP_STATE.state_typ_cd = CORP_STATE.state_typ_cd
                    left join JURISDICTION on JURISDICTION.corp_num = corp.corp_num
                    join corp_type ct on ct.corp_typ_cd = corp.corp_typ_cd
                    join event on corp.corp_num = event.corp_num
                    left join filing on event.event_id = filing.event_id and filing.filing_typ_cd in ('OTANN', 'ANNBC')
                where {corp_type_condition} corp.corp_num=:corp_num
                order by filing.period_end_dt desc nulls last
                """,
                corp_num=identifier
            )
            business = cursor.fetchone()
            if not business:
                raise BusinessNotFoundException(identifier=identifier)

            # add column names to resultset to build out correct json structure and make manipulation below more robust
            # (better than column numbers)
            business = dict(zip([x[0].lower() for x in cursor.description], business))
            # get all assumed, numbered/corporation, translation names
            corp_names = CorpName.get_current(cursor=cursor, corp_num=identifier)
            assumed_name = None
            corp_name = None
            for name_obj in corp_names:
                if name_obj.type_code == CorpName.TypeCodes.ASSUMED.value:  # pylint: disable=no-else-break
                    assumed_name = name_obj.corp_name
                    break
                elif name_obj.type_code in [CorpName.TypeCodes.CORP.value, CorpName.TypeCodes.NUMBERED_CORP.value]:
                    corp_name = name_obj.corp_name

            # get last ledger date from EVENT table and add to business record
            # note - FILE event type is correct for new filings; CONVOTHER is for events/filings pulled over from COBRS
            cursor.execute(
                """
                select max(EVENT_TIMESTMP) from EVENT
                where EVENT_TYP_CD in ('FILE', 'CONVOTHER') and CORP_NUM=:corp_num
                """,
                corp_num=identifier
            )
            last_ledger_timestamp = cursor.fetchone()[0]
            business['last_ledger_timestamp'] = last_ledger_timestamp
            # jurisdiction
            if business.get('can_jur_typ_cd'):
                # This is an XPRO, get correct jurisdiction
                business['jurisdiction'] = business['can_jur_typ_cd']
                if business['can_jur_typ_cd'] == 'OT':
                    business['jurisdiction'] = business['othr_juris_desc']
            else:
                # This is NOT an XPRO so set to BC
                business['jurisdiction'] = 'BC'

            # convert to Business object
            business_obj = Business()
            business_obj.business_number = business['bn_15']
            business_obj.corp_name = assumed_name if assumed_name else corp_name
            business_obj.corp_num = business['corp_num']
            business_obj.corp_state = business['corp_state']
            business_obj.corp_state_class = business['corp_state_class']
            business_obj.corp_type = business['corp_typ_cd']
            business_obj.email = business['admin_email']
            business_obj.founding_date = convert_to_json_datetime(business['recognition_dts'])
            business_obj.good_standing = cls.is_in_good_standing(business, cursor)
            business_obj.jurisdiction = business['jurisdiction']
            business_obj.home_recogn_dt = convert_to_json_datetime(business['home_recogn_dt'])
            business_obj.home_juris_num = business['home_juris_num']
            business_obj.home_company_nme = business['home_company_nme']
            business_obj.last_agm_date = convert_to_json_date(business['last_agm_date'])
            business_obj.last_ar_date = convert_to_json_date(business['period_end_dt']) if business['period_end_dt'] \
                else convert_to_json_date(business['last_agm_date'])
            business_obj.last_ledger_timestamp = convert_to_json_datetime(business['last_ledger_timestamp'])
            business_obj.status = business['state']
            business_obj.admin_freeze = business['admin_freeze']

            return business_obj

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err

    @classmethod
    def create_corporation(cls, con, filing_info: Dict):
        """Insert a new business from an incorporation filing."""
        try:
            business = Business()
            business.corp_name = filing_info['business']['legalName']
            business.corp_num = filing_info['business']['identifier']
            business.founding_date = convert_to_pacific_time(filing_info['header']['learEffectiveDate'])

            business.corp_type = filing_info['business']['legalType']
            business.corp_num = cls.get_colin_identifier(business.corp_num, business.corp_type)

            cursor = con.cursor()

            # Expand query as NR data/ business info becomes more aparent
            cursor.execute(
                """
                insert into CORPORATION (CORP_NUM, CORP_TYP_CD, RECOGNITION_DTS)
                values (:corp_num, :corp_type, TO_TIMESTAMP_TZ(:recognition_date,'YYYY-MM-DD"T"HH24:MI:SS.FFTZH:TZM'))
                """,
                corp_num=business.corp_num,
                corp_type=business.corp_type,
                recognition_date=business.founding_date
            )

            return business

        except Exception as err:
            current_app.logger.error('Error inserting business.')
            raise err

    @classmethod
    def create_corp_restriction(cls, cursor, event_id: str, corp_num: str, provisions: bool):
        """Create corp restriction entry for business."""
        try:
            value = 'Y' if provisions else 'N'
            cursor.execute(
                """
                insert into corp_restriction (start_event_id, corp_num, restriction_ind)
                values (:event_id, :corp_num, :value)
                """,
                event_id=event_id,
                corp_num=corp_num,
                value=value
            )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def create_corp_state(cls, cursor, corp_num, event_id):
        """Add record to the CORP STATE table on incorporation."""
        try:
            cursor.execute(
                """
                insert into CORP_STATE(CORP_NUM, START_EVENT_ID, STATE_TYP_CD)
                values (:corp_num, :event_id, 'ACT')
                """,
                corp_num=corp_num,
                event_id=event_id
            )

        except Exception as err:
            current_app.logger.error('Error inserting corp state.')
            raise err

    @classmethod
    def create_resolution(cls, cursor, corp_num: str, event_id: str, resolution_date: str):
        """Create a new resolution entry for a company."""
        try:
            cursor.execute(
                """
                insert into resolution(corp_num, start_event_id, resolution_dt)
                values (:corp_num, :event_id, TO_DATE(:res_date, 'YYYY-mm-dd'))
                """,
                corp_num=corp_num,
                event_id=event_id,
                res_date=resolution_date
            )

        except Exception as err:
            current_app.logger.error('Error inserting resolution.')
            raise err

    @classmethod
    def end_resolution(cls, cursor, corp_num: str, event_id: str, resolution_date: str):
        """End resolution entry for a company."""
        try:
            cursor.execute(
                """
                UPDATE resolution set end_event_id = :event_id
                WHERE
                    corp_num = :corp_num AND
                    end_event_id is null AND
                    resolution_dt = TO_DATE(:res_date, 'YYYY-mm-dd')
                """,
                corp_num=corp_num,
                event_id=event_id,
                res_date=resolution_date
            )

        except Exception as err:
            current_app.logger.error('Error inserting resolution.')
            raise err

    @classmethod
    def get_corp_restriction(cls, cursor, corp_num: str, event_id: str = None):
        """Get provisions removed flag for this event."""
        try:
            if not event_id:
                cursor.execute(
                    """
                    SELECT *
                    FROM corp_restriction
                    WHERE corp_num=:corp_num and end_event_id is null
                    """,
                    corp_num=corp_num
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM corp_restriction
                    WHERE corp_num=:corp_num and start_event_id>=:event_id
                      and (end_event_id<=:event_id or end_event_id is null)
                    """,
                    event_id=event_id,
                    corp_num=corp_num
                )
            if restrictions := cursor.fetchall():
                description = cursor.description
                return dict(zip([x[0].lower() for x in description], restrictions[0]))
            return False
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def end_current_corp_restriction(cls, cursor, event_id: str, corp_num: str):
        """End current corp restriction entry for business."""
        try:
            cursor.execute(
                """
                UPDATE corp_restriction
                SET end_event_id = :event_id
                WHERE corp_num = :corp_num and end_event_id is NULL
                """,
                event_id=event_id,
                corp_num=corp_num
            )
        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def update_corporation(cls, cursor, corp_num: str, date: str = None, annual_report: bool = False,
                           last_ar_filed_dt: str = None):
        # pylint: disable=too-many-arguments
        """Update corporation record."""
        try:
            if annual_report:
                if date:
                    cursor.execute(
                        """
                        UPDATE corporation
                        SET LAST_AR_FILED_DT = TO_DATE(:last_ar_filed_dt, 'YYYY-mm-dd'),
                        LAST_AGM_DATE = TO_DATE(:agm_date, 'YYYY-mm-dd'), LAST_LEDGER_DT = sysdate
                        WHERE corp_num = :corp_num
                        """,
                        agm_date=date,
                        corp_num=corp_num,
                        last_ar_filed_dt=last_ar_filed_dt
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE corporation
                        SET LAST_AR_FILED_DT = TO_DATE(:last_ar_filed_dt, 'YYYY-mm-dd'),
                        LAST_LEDGER_DT = sysdate
                        WHERE corp_num = :corp_num
                        """,
                        corp_num=corp_num,
                        last_ar_filed_dt=last_ar_filed_dt
                    )

            else:
                cursor.execute(
                    """
                    UPDATE corporation
                    SET LAST_LEDGER_DT = sysdate
                    WHERE corp_num = :corp_num
                    """,
                    corp_num=corp_num
                )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def update_corp_state(cls, cursor, event_id: str, corp_num: str, state: str = 'ACT'):
        """Update corporation state."""
        try:
            cursor.execute(
                """
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
            cursor.execute(
                """
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
    def update_corp_type(cls, cursor, corp_num: str, corp_type: str):
        """Update corp type code in corporations table."""
        try:
            if corp_type not in [x.value for x in Business.TypeCodes.__members__.values()]:
                current_app.logger.error(f'Tried to update {corp_num} with invalid corp type code {corp_type}')
                raise Exception  # pylint: disable=broad-exception-raised

            cursor.execute(
                """
                UPDATE corporation
                SET corp_typ_cd = :corp_type
                WHERE corp_num = :corp_num
                """,
                corp_num=corp_num,
                corp_type=corp_type
            )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def update_corp_frozen_type(cls, cursor, corp_num: str, corp_frozen_type_code: str):
        """Update corp frozen type code in corporations table."""
        try:
            if corp_frozen_type_code not in [x.value for x in Business.CorpFrozenTypes.__members__.values()]:
                current_app.logger.error(f'Tried to update {corp_num} with invalid corp frozen type \
                                            code {corp_frozen_type_code}')
                raise ValueError(f'Tried to update {corp_num} with invalid corp frozen type \
                                    code {corp_frozen_type_code}')

            cursor.execute(
                """
                UPDATE corporation
                SET corp_frozen_typ_cd = :corp_frozen_type_code
                WHERE corp_num = :corp_num
                """,
                corp_num=corp_num,
                corp_frozen_type_code=corp_frozen_type_code
            )

        except Exception as err:
            current_app.logger.error(err.with_traceback(None))
            raise err

    @classmethod
    def get_founding_date(cls, cursor, corp_num: str) -> str:
        """Return the founding date of the company."""
        cursor.execute(
            """
            SELECT recognition_dts
            FROM corporation
            WHERE corp_num=:corp_num
            """,
            corp_num=corp_num
        )
        founding_date = cursor.fetchone()[0]
        return founding_date

    @classmethod
    def get_next_corp_num(cls, con, corp_type: str) -> str:
        """Retrieve the next available corporation number and advance by one."""
        try:
            cursor = con.cursor()
            cursor.execute(
                """
                SELECT id_num
                FROM system_id
                WHERE id_typ_cd = :corp_type
                FOR UPDATE
                """,
                corp_type=corp_type
            )
            corp_num = cursor.fetchone()

            if corp_num:
                cursor.execute(
                    """
                    UPDATE system_id
                    SET id_num = :new_num
                    WHERE id_typ_cd = :corp_type
                    """,
                    new_num=corp_num[0] + 1,
                    corp_type=corp_type
                )

            return '%07d' % corp_num  # pylint: disable=consider-using-f-string
        except Exception as err:
            current_app.logger.error('Error looking up corp_num')
            raise err

    @classmethod
    def get_resolutions(cls, cursor, corp_num: str, event_id: str = None) -> List:
        """Get all resolution dates for a company or for a specific event id."""
        try:
            event_query = ''
            if event_id:
                event_query = f'and start_event_id = {event_id}'
            else:
                event_query = 'and end_event_id is null'
            resolution_dates = []
            cursor.execute(
                f"""
                select resolution_dt from resolution
                where corp_num = :corp_num {event_query}
                order by resolution_dt desc
                """,
                corp_num=corp_num
            )
            resolution_oracle_dates = cursor.fetchall()
            for date in resolution_oracle_dates:
                resolution_dates.append(convert_to_json_date(date[0]))
            return resolution_dates
        except Exception as err:
            current_app.logger.error(f'Error looking up resolution dates for {corp_num}')
            raise err

    @classmethod
    def reset_corporations(cls, cursor, event_info: List, event_ids: List):
        """Reset the corporations to what they were before the given events."""
        if not event_info:
            return

        dates_by_corp_num = cls._get_last_ar_dates_for_reset(cursor=cursor, event_info=event_info, event_ids=event_ids)
        for item in dates_by_corp_num:
            try:
                cursor.execute(
                    """
                    UPDATE corporation
                    SET LAST_AR_FILED_DT = :ar_filed_date, LAST_AGM_DATE = :agm_date, LAST_LEDGER_DT = :event_date
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
    def reset_corp_states(cls, cursor, event_ids: List):
        """Reset the corp states to what they were before the given events."""
        if not event_ids:
            return

        # delete corp_state rows created on these events
        try:
            cursor.execute(
                f"""
                DELETE FROM corp_state
                WHERE start_event_id in ({stringify_list(event_ids)})
                """
            )
        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed delete corp_state rows for events {event_ids}')
            raise err

        # reset corp_state rows ended on these events
        try:
            cursor.execute(
                f"""
                UPDATE corp_state
                SET end_event_id = null
                WHERE end_event_id in ({stringify_list(event_ids)})
                """
            )
        except Exception as err:
            current_app.logger.error(f'Error in Business: Failed reset ended corp_state rows for events {event_ids}')
            raise err

    @staticmethod
    def is_in_good_standing(business: dict, cursor) -> Optional[bool]:
        """Return the good standing value of the business."""
        if business['corp_state_class'] != 'ACT' or business.get('xpro_jurisdiction', '') in ['AB', 'MB', 'SK']:
            # good standing is irrelevant to non active and nwpta businesses
            return None
        if business['corp_class'] in ['BC'] or business['corp_typ_cd'] in ['LLC', 'LIC', 'A', 'B']:
            if business.get('corp_state') in ['D1A', 'D1F', 'D1T', 'D2A', 'D2F', 'D2T', 'LIQ', 'LRL', 'LRS']:
                # Dissolution state or Liquidation or Limited Restoration or  is NOT in good standing
                #   - updates into Dissolution states occur irregularly via batch job
                #   - updates out of these states occur immediately when filing is processed
                #     (can rely on this for a business being NOT in good standing only)
                return False

            requires_transition = business['recognition_dts'] and business['recognition_dts'] < datetime(2004, 3, 29)
            if requires_transition and business['transition_dt'] is None:
                # Businesses incorporated prior to March 29th, 2004 must file a transition filing
                cursor.execute(
                    """
                    SELECT max(f.effective_dt)
                    FROM event e join filing f on f.event_id = e.event_id
                    WHERE f.filing_typ_cd in ('RESTF','RESXF')
                        and e.corp_num=:corp_num
                    """, corp_num=business['corp_num'])
                last_restoration_date = cursor.fetchone()
                if last_restoration_date and last_restoration_date[0]:
                    # restored businesses that require transition have 1 year to do so
                    return last_restoration_date[0] + datedelta(years=1) > datetime.utcnow()
                return False
            if last_file_date := (business['last_ar_filed_dt'] or business['recognition_dts']):
                # return if the last AR or founding date was within a year and 2 months
                return last_file_date + datedelta(years=1, months=2, days=1) > datetime.utcnow()
        return None
