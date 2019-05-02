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

from colin_api.exceptions import FilingNotFoundException
from colin_api.resources.db import db


class Filing():
    """Class to contain all model-like functions such as getting and setting from database."""

    @classmethod
    def find_filing(cls, identifier: str = None, filing_type: str = None, year: int = None):
        """Return a Business by the id assigned by the Registrar."""
        if not identifier or not filing_type:
            return None

        try:

            # set filing type code from filing_type (string)
            if filing_type == 'annual_report':
                # new filings are FILE, filings imported from COBRS are OTANN
                filing_type_code = "FILE', 'OTANN"
            else:
                filing_type_code = 'FILE'

            # build base querystring
            querystring = (
                "select event.EVENT_TIMESTMP, EFFECTIVE_DT, AGM_DATE, PERIOD_END_DT, NOTATION, "
                "FIRST_NME, LAST_NME, MIDDLE_NME, EMAIL_ADDR "
                "from EVENT "
                "join FILING on EVENT.EVENT_ID = FILING.EVENT_ID "
                "left join FILING_USER on EVENT.EVENT_ID = FILING_USER.EVENT_ID "
                "join LEDGER_TEXT on EVENT.EVENT_ID = LEDGER_TEXT.EVENT_ID "
                "where CORP_NUM='{}' and FILING_TYP_CD in ('{}') ".format(identifier, filing_type_code)
            )

            # condition by year on period end date - for coops, this is same as AGM date; for corps, this is financial
            # year end date.
            if year:
                querystring += " AND extract(year from PERIOD_END_DT) = {}".format(year)

            querystring += " order by EVENT_TIMESTMP desc"

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

            # if email is blank, set as empty tring
            if not filing['email_addr']:
                filing['email_addr'] = ''

            return {
                'filing_header': {
                    'date': filing['event_timestmp'],
                    'name': filing_type
                },
                'filing_body': {
                    'annual_general_meeting_date': agm_date,
                    'certified_by': filing_user_name,
                    'email': filing['email_addr']
                }
            }

        except FilingNotFoundException as err:
            # pass through exception to caller
            raise err

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))

            # pass through exception to caller
            raise err
