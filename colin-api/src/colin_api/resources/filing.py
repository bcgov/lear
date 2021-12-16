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
from http import HTTPStatus

from flask import current_app, jsonify, request
from flask_restx import Resource, cors
from registry_schemas import validate

from colin_api.exceptions import GenericException
from colin_api.models import Business
from colin_api.models.filing import DB, Filing
from colin_api.resources.business import API
from colin_api.utils import convert_to_pacific_time
from colin_api.utils.util import cors_preflight


@cors_preflight('GET, POST')
@API.route('/<string:legal_type>/<string:identifier>/filings/<string:filing_type>')
@API.route('/<string:legal_type>/<string:identifier>/filings/<string:filing_type>/<string:filing_sub_type>')
class FilingInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(legal_type, identifier, filing_type, filing_sub_type=None):
        """Return the complete filing info or historic (pre-bob-date=2019-03-08) filings."""
        try:
            if legal_type not in [x.value for x in Business.LearBusinessTypes]:
                return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

            # get optional parameters (event_id / year)
            event_id = request.args.get('eventId', None)
            year = request.args.get('year', None)
            if year:
                year = int(year)

            # convert identifier if BC legal_type
            if legal_type in Business.CORP_TYPE_CONVERSION[Business.LearBusinessTypes.BCOMP.value]:
                identifier = identifier[-7:]

            # get business
            corp_types = Business.CORP_TYPE_CONVERSION[legal_type]
            business = Business.find_by_identifier(identifier, corp_types)

            # get filings history from before bob-date
            if filing_type == 'historic':
                historic_filings_info = Filing.get_historic_filings(business=business)
                return jsonify(historic_filings_info)

            # else get filing
            filing = Filing()
            filing.business = business
            filing.filing_type = filing_type
            filing.filing_sub_type = filing_sub_type

            filing.event_id = event_id
            filing = Filing.get_filing(filing=filing, year=year)
            return jsonify(filing.as_dict())

        except GenericException as err:  # pylint: disable=duplicate-code
            return jsonify(
                {'message': err.error}), err.status_code

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': 'Error when trying to retrieve business record from COLIN'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    @cors.crossdomain(origin='*')
    def post(legal_type, identifier, **kwargs):
        """Create a new filing."""
        # pylint: disable=unused-argument,too-many-branches; filing_type is only used for the get
        try:
            if legal_type not in [x.value for x in Business.LearBusinessTypes]:
                return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

            json_data = request.get_json()
            if not json_data:
                return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST

            # validate schema
            is_valid, errors = validate(json_data, 'filing', validate_schema=True)
            if not is_valid:
                for err in errors:
                    print(err.message)
                return jsonify(
                    {'message': 'Error: Invalid Filing schema'}), HTTPStatus.BAD_REQUEST

            json_data = json_data.get('filing', None)

            # ensure that the business in the AR matches the business in the URL
            if identifier != json_data['business']['identifier']:
                return jsonify(
                    {'message': 'Error: Identifier in URL does not match identifier in filing data'}
                ), HTTPStatus.BAD_REQUEST

            # convert identifier if BC legal_type
            if legal_type in Business.CORP_TYPE_CONVERSION[Business.LearBusinessTypes.BCOMP.value]:
                identifier = identifier[-7:]

            corp_types = Business.CORP_TYPE_CONVERSION[legal_type]
            if json_data.get('correction', None):
                filing_list = {'correction': json_data['correction']}
            else:
                filing_list = {
                    'changeOfAddress': json_data.get('changeOfAddress', None),
                    'changeOfDirectors': json_data.get('changeOfDirectors', None),
                    'annualReport': json_data.get('annualReport', None),
                    'incorporationApplication': json_data.get('incorporationApplication', None),
                    'alteration': json_data.get('alteration', None),
                    'transition': json_data.get('transition', None),
                    'registrarsNotation': json_data.get('registrarsNotation', None),
                    'registrarsOrder': json_data.get('registrarsOrder', None),
                    'courtOrder': json_data.get('courtOrder', None),
                    'dissolution': json_data.get('dissolution', None),
                    'specialResolution': json_data.get('specialResolution', None)
                }

            # Filter out null-values in the filing_list dictionary
            filing_list = {k: v for k, v in filing_list.items() if filing_list[k]}
            try:
                # get db connection and start a session, in case we need to roll back
                con = DB.connection
                con.begin()
                filings_added = FilingInfo._add_filings(con, json_data, filing_list, identifier, corp_types)

                # return the completed filing data
                completed_filing = Filing()
                # get business info again - could have changed since filings were applied
                completed_filing.business = Business.find_by_identifier(identifier, corp_types, con)
                completed_filing.body = {}
                for filing_info in filings_added:
                    sub_filing = Filing()
                    sub_filing.business = completed_filing.business
                    sub_filing.filing_type = filing_info['filing_type']
                    sub_filing.filing_sub_type = filing_info['filing_sub_type']
                    sub_filing.event_id = filing_info['event_id']
                    sub_filing = Filing.get_filing(filing=sub_filing, con=con)

                    if completed_filing.header:
                        completed_filing.header['colinIds'].append(sub_filing.event_id)
                        # annual report is the only filing with sub filings underneath it
                        if sub_filing.filing_type == 'annualReport':
                            completed_filing.header['name'] = 'annualReport'
                    else:
                        completed_filing.header = sub_filing.header
                    completed_filing.body.update({sub_filing.filing_type: sub_filing.body})

                # success! commit the db changes
                con.commit()
                return jsonify(completed_filing.as_dict()), HTTPStatus.CREATED

            except Exception as db_err:
                current_app.logger.error('failed to file - rolling back partial db changes.')
                if con:
                    con.rollback()
                raise db_err

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify(
                {'message': f'Error when trying to file for business {identifier}'}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    def _add_filings(con, json_data: dict, filing_list: list, identifier: str, corp_types: list) -> list:
        """Process all parts of the filing."""
        filings_added = []
        for filing_type in filing_list:
            filing = Filing()
            filing.header = json_data['header']
            filing.filing_date = filing.header['date']
            filing.filing_type = filing_type
            filing_body = filing_list[filing_type]
            filing.filing_sub_type = Filing.get_filing_sub_type(filing_type, filing_body)
            filing.body = filing_body
            # get utc lear effective date and convert to pacific time for insert into oracle
            filing.effective_date = convert_to_pacific_time(filing.header['learEffectiveDate'])

            if filing_type != 'incorporationApplication':
                filing.business = Business.find_by_identifier(identifier, corp_types, con)
            else:
                filing.business = Business.create_corporation(con, json_data)
            # add the new filing
            event_id = Filing.add_filing(con, filing)
            filings_added.append({'event_id': event_id,
                                  'filing_type': filing_type,
                                  'filing_sub_type': filing.filing_sub_type})
        return filings_added
