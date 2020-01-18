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
from flask import current_app, jsonify, request
from flask_restplus import Namespace, Resource, cors

from colin_api.models.reset import Reset
from colin_api.utils.util import cors_preflight


API = Namespace('Reset', description='Reset endpoint for changes made by COOPER')


@cors_preflight('POST')
@API.route('/cooper')
class ResetInfo(Resource):
    """Reset class containing calls to revert changes made by COOPER."""

    @staticmethod
    @cors.crossdomain(origin='*')
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
