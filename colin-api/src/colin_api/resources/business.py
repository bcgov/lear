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
from flask import current_app, jsonify
from flask_restplus import Namespace, Resource, cors

from colin_api.resources.db import db
from colin_api.utils.util import cors_preflight

API = Namespace('businesses', description='Colin API Services - Businesses')


@cors_preflight('GET')
@API.route('/<string:identifier>')
class Info(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier):
        """Return the complete business info."""
        try:
            # get record
            cursor = db.connection.cursor()
            cursor.execute(
                "select corp.CORP_NUM as identifier, CORP_FROZEN_TYP_CD, corp_typ_cd type, "
                "LAST_AR_FILED_DT last_ar_filed_date, LAST_AGM_DATE, "
                "corp_op_state.full_desc as state, t_name.corp_nme as legal_name, "
                "t_assumed_name.CORP_NME as assumed_name, RECOGNITION_DTS as founding_date,"
                "TILMA_INVOLVED_IND, TILMA_CESSATION_DT, BN_15 as business_number, "
                "CAN_JUR_TYP_CD, OTHR_JURIS_DESC, HOME_JURIS_NUM "
                "from CORPORATION corp "
                "left join CORP_NAME t_name on t_name.corp_num = corp.corp_num and t_name.CORP_NAME_TYP_CD='CO' "
                "AND t_name.END_EVENT_ID is null "
                "left join CORP_NAME t_assumed_name on t_assumed_name.corp_num = corp.corp_num "
                "and t_assumed_name.CORP_NAME_TYP_CD='AS' AND t_assumed_name.END_EVENT_ID is null "
                "join CORP_STATE on CORP_STATE.corp_num = corp.corp_num and CORP_STATE.end_event_id is null "
                "join CORP_OP_STATE on CORP_OP_STATE.state_typ_cd = CORP_STATE.state_typ_cd "
                "left join JURISDICTION on JURISDICTION.corp_num = corp.corp_num "
                "where corp_typ_cd = 'CP'"  # only include coops (not xpro coops) for now
                "and corp.CORP_NUM='{}'".format(identifier))
            business = cursor.fetchone()
            print(business)

            if not business:
                return jsonify({'message': f'{identifier} not found'}), 404

            # add column names to resultset to build out correct json structure and make manipulation below more robust (better than column numbers)
            business = dict(zip([x[0].lower() for x in cursor.description], business))
            current_app.logger.debug(business)

            # if this is an XPRO, get correct jurisdiction; otherwise, it's BC
            # DISABLED (if False) until XPROs are implemented
            if False and business['type'] == 'XCP':
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
                business['last_ar_filed_date'] is not None and type(business['last_ar_filed_date']) is datetime and \
                business['last_agm_date'] is not None and type(business['last_agm_date']) is datetime:

                if business['last_ar_filed_date'] > business['last_agm_date']:
                    business['status'] = 'In Good Standing'
            else:
                business['status'] = business['state']


            # remove unnecessary fields
            del business['home_juris_num']
            del business['can_jur_typ_cd']
            del business['othr_juris_desc']
            del business['assumed_name']
            del business['state']

            retval = {
                'business': {
                    'business_info': business
                }
            }


            return jsonify(retval)

        except Exception as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': "Error when trying to retrieve business record from COLIN"}), 500
