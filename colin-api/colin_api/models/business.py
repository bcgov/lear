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
from colin_api.utils import convert_to_json_date, convert_to_json_datetime


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
    def find_by_identifier(cls, identifier: str = None):  # pylint: disable=too-many-statements;
        """Return a Business by identifier."""
        business = None
        if not identifier:
            return None

        try:
            # get record
            cursor = DB.connection.cursor()
            cursor.execute("""
                select corp.CORP_NUM as identifier, CORP_FROZEN_TYP_CD, corp_typ_cd type,
                LAST_AR_FILED_DT last_ar_filed_date, LAST_AGM_DATE,
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
                where corp_typ_cd = 'CP'
                and corp.CORP_NUM=:corp_num""", corp_num=identifier)
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
                if business['can_jur_typ_cd'] == 'OT':
                    business['jurisdiction'] = business['othr_juris_desc']
                else:
                    business['jurisdiction'] = business['can_jur_typ_cd']
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

                if business['last_ar_filed_date'] > business['last_agm_date']:
                    business['status'] = 'In Good Standing'
                else:
                    business['status'] = business['state']
            else:
                business['status'] = business['state']

            # convert dates and date-times to correct json format and convert to camel case for schema names
            business['foundingDate'] = convert_to_json_date(business['founding_date'])
            business['lastAgmDate'] = convert_to_json_date(business['last_agm_date'])
            business['lastArFiledDate'] = convert_to_json_date(business['last_ar_filed_date'])
            business['lastLedgerTimestamp'] = convert_to_json_datetime(business['last_ledger_timestamp'])

            business['businessNumber'] = business['business_number']
            business['corpState'] = business['corp_state']
            business['legalName'] = business['legal_name']

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
