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
from registry_schemas import validate

from colin_api.exceptions import GenericException
from colin_api.models import Business, Filing
from colin_api.resources.business import API
from colin_api.utils.util import cors_preflight


@cors_preflight('GET, POST')
@API.route('/<string:identifier>/filings/<string:filing_type>')
class FilingInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, filing_type):
        """Return the complete filing info."""
        try:

            # get optional parameters (event_id / year)
            event_id = request.args.get('eventId', None)
            year = request.args.get('year', None)
            if year:
                year = int(year)

            # get business
            business = Business.find_by_identifier(identifier)

            # get filing
            filing = Filing.find_filing(business=business, event_id=event_id, filing_type=filing_type, year=year)
            return jsonify(filing.as_dict())

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}), 500

    @staticmethod
    @cors.crossdomain(origin='*')
    def post(identifier, filing_type):
        """Create a new filing."""
        try:
            json_data = request.get_json()
            if not json_data:
                return jsonify({'message': 'No input data provided'}), 400

            # validate schema
            is_valid, errors = validate(json_data, 'filing', validate_schema=True)
            if not is_valid:
                for err in errors:
                    print(err.message)
                return jsonify(
                    {'message': 'Error: Invalid Filing schema'}), 400

            json_data = json_data.get('filing', None)

            # ensure that the business in the AR matches the business in the URL
            if identifier != json_data['business']['identifier']:
                return jsonify(
                    {'message': 'Error: Identifier in URL does not match identifier in filing data'}), 400

            filing = Filing()
            filing.header = json_data['header']

            filing.filing_type = filing_type
            filing.body = json_data[filing.filing_type]

            filing.business = Business.find_by_identifier(identifier)

            # add the new filing
            event_id = Filing.add_filing(filing)

            # return the completed filing data
            completed_filing = Filing.find_filing(business=filing.business, event_id=event_id,
                                                  filing_type=filing.filing_type)
            return jsonify(completed_filing.as_dict()), 200

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}), 500
