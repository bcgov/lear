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
from flask import current_app, jsonify, request
from flask_restplus import Resource, cors

from colin_api.exceptions import GenericException
from colin_api.models import Business, Filing
from colin_api.resources.business import API
from colin_api.utils.util import cors_preflight


@cors_preflight('GET')
@API.route('/<string:identifier>/filings/<string:filing_type>')
class FilingInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, filing_type):
        """Return the complete business info."""
        try:

            # get optional YEAR parameter
            year = request.args.get('year', None)
            if year:
                year = int(year)

            # get business
            business = Business.find_by_identifier(identifier)

            # get filing
            filing = Filing.find_filing(identifier, filing_type, year)

            return jsonify({
                'filing': {
                    'filing_header': filing['filing_header'],
                    filing_type: filing['filing_body'],
                    'business': business,
                }
            })

        except GenericException as err:
            return jsonify(
                {'message': err.error}), err.status_code

        except ValueError as err:
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}), 500
