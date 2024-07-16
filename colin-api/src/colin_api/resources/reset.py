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
"""Reset endpoints for COLIN.

Currently this only resets changes made to COOP data made with user COOPER
"""
import json
from flask import current_app, jsonify, request
from flask_restx import Namespace, Resource, cors, fields

from colin_api.models.reset import Reset
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


API = Namespace('Reset', description='Reset endpoint for changes made by COOPER')


@cors_preflight('POST')
@API.route('/cooper')
class ResetInfo(Resource):
    """Reset class containing calls to revert changes made by COOPER."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def post():
        """Reset the changes in COLIN made by COOPER."""
        try:
            json_data = request.get_json()
            start_date = json_data.get('start_date', None)
            end_date = json_data.get('end_date', None)
            identifiers = json_data.get('identifiers', None)
            filing_types = json_data.get('filing_types', None)

            Reset.reset_filings(
                start_date=start_date,
                end_date=end_date,
                identifiers=identifiers,
                filing_types=filing_types
            )
            return jsonify({'message': 'Successfully reset COLIN.'}), 200

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify({'message': 'Error when trying to reset COLIN'}), 500


@cors_preflight('POST')
@API.route('/by_event_id')
class ResetByEventId(Resource):
    """Reset filing(s) based on the provided event_id, or array of event_ids.
      This is only tested to work on Annual Reports, ymmv"""

    eventResetParser = API.parser()
    eventResetParser.add_argument(
        'event_ids',
        type=list,
        help='The list of event ids to reset. Can be one id',
        location='json',
        required=True)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    @API.expect(eventResetParser)
    def post():
        """Reset filing(s) based on the provided event_id, or array of event_ids.
        This is only tested to work on Annual Reports, ymmv"""
        try:

            event_ids = API.payload.get('event_ids', None)

            Reset.reset_filings_by_event(
                event_ids=event_ids
            )

            return jsonify({'message': "Reset for event ids " + json.dumps(event_ids)}), 200

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify({'message': 'Error when trying to reset COLIN by event ids'}), 500
