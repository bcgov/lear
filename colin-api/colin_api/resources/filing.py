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

from colin_api.exceptions import FilingNotFoundException, GenericException
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
        """Return the complete filing info or historic (pre-bob-date=2019-03-08) filings."""
        try:
            # get optional parameters (event_id / year)
            event_id = request.args.get('eventId', None)
            year = request.args.get('year', None)
            if year:
                year = int(year)

            # get business
            business = Business.find_by_identifier(identifier)

            # get filings history from before bob-date
            if filing_type == 'historic':
                historic_filings_info = Filing.get_historic_filings(business=business)
                return jsonify(historic_filings_info)

            # else get filing
            filing = Filing.get_filing(business=business, event_id=event_id, filing_type=filing_type, year=year)
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
    def post(identifier, **kwargs):  # pylint: disable=unused-argument; filing_type is only used for the get
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

            filing_list = {'changeOfAddress': json_data.get('changeOfAddress', None),
                           'changeOfDirectors': json_data.get('changeOfDirectors', None),
                           'annualReport': json_data.get('annualReport', None)}

            # ensure that the business in the AR matches the business in the URL
            if identifier != json_data['business']['identifier']:
                return jsonify(
                    {'message': 'Error: Identifier in URL does not match identifier in filing data'}), 400

            filings_added = []
            for filing_type in filing_list:
                if filing_list[filing_type]:
                    filing = Filing()
                    filing.business = Business.find_by_identifier(identifier)
                    filing.header = json_data['header']
                    filing.filing_type = filing_type
                    filing.body = filing_list[filing_type]

                    # add the new filing
                    event_id = Filing.add_filing(filing)
                    filings_added.append({'event_id': event_id, 'filing_type': filing_type})

            # return the completed filing data
            completed_filing = Filing()
            completed_filing.header = json_data['header']
            # get business info again - could have changed since filings were applied
            completed_filing.business = Business.find_by_identifier(identifier)
            completed_filing.body = {}
            for filing_info in filings_added:
                filing = Filing.get_filing(business=completed_filing.business, event_id=filing_info['event_id'],
                                           filing_type=filing_info['filing_type'])
                if not filing:
                    raise FilingNotFoundException(identifier=identifier, filing_type=filing_info['filing_type'],
                                                  event_id=filing_info['event_id'])
                completed_filing.body.update({filing_info['filing_type']: filing.body})

            return jsonify(completed_filing.as_dict()), 201

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}), 500
