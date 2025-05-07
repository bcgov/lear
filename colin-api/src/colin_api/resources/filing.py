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

from colin_api.exceptions import GenericException
from colin_api.models import Business
from colin_api.models.filing import DB, Filing
from colin_api.resources.business import API
from colin_api.utils import convert_to_pacific_time
from colin_api.utils.auth import COLIN_SVC_ROLE, jwt
from colin_api.utils.util import cors_preflight


@cors_preflight('GET, POST')
@API.route('/<string:legal_type>/<string:identifier>/filings/<string:filing_type>')
@API.route('/<string:legal_type>/<string:identifier>/filings/<string:filing_type>/<string:filing_sub_type>')
class FilingInfo(Resource):
    """Meta information about the overall service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def get(legal_type, identifier, filing_type, filing_sub_type=None):
        """Return the complete filing info or historic (pre-bob-date=2019-03-08) filings."""
        try:
            if legal_type not in [x.value for x in Business.TypeCodes]:
                return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

            # get optional parameters (event_id / year)
            event_id = request.args.get('eventId', None)
            year = request.args.get('year', None)
            if year:
                year = int(year)

            # convert identifier if BC legal_type
            identifier = Business.get_colin_identifier(identifier, legal_type)

            # get business
            business = Business.find_by_identifier(identifier)

            # get future effective filings
            if filing_type == 'future':
                future_effective_filings_info = Filing.get_future_effective_filings(business=business)
                return jsonify(future_effective_filings_info)

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
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def post(legal_type, identifier, **kwargs):
        """Create a new filing."""
        # pylint: disable=too-many-return-statements,unused-argument,too-many-branches;
        # filing_type is only used for the get
        try:
            if legal_type not in [x.value for x in Business.TypeCodes]:
                return jsonify({'message': 'Must provide a valid legal type.'}), HTTPStatus.BAD_REQUEST

            json_data = request.get_json()
            if not json_data:
                return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST

            # validate schema
            # is_valid, errors = validate(json_data, 'filing', validate_schema=True)
            # if not is_valid:
            #     for err in errors:
            #         print(err.message)
            #     return jsonify(
            #         {'message': 'Error: Invalid Filing schema'}), HTTPStatus.BAD_REQUEST

            json_data = json_data.get('filing', None)

            # ensure that the business in the AR matches the business in the URL
            if identifier != json_data['business']['identifier']:
                return jsonify(
                    {'message': 'Error: Identifier in URL does not match identifier in filing data'}
                ), HTTPStatus.BAD_REQUEST

            # setting this for lear business check as identifier is converted from lear to colin below
            lear_identifier = identifier

            # convert identifier if BC legal_type
            identifier = Business.get_colin_identifier(identifier, legal_type)

            if json_data.get('correction', None):
                filing_list = {'correction': json_data['correction']}
            else:
                filing_list = {
                    'agmExtension': json_data.get('agmExtension', None),
                    'agmLocationChange': json_data.get('agmLocationChange', None),
                    'alteration': json_data.get('alteration', None),
                    'amalgamationApplication': json_data.get('amalgamationApplication', None),
                    'amalgamationOut': json_data.get('amalgamationOut', None),
                    'annualReport': json_data.get('annualReport', None),
                    'changeOfAddress': json_data.get('changeOfAddress', None),
                    'changeOfDirectors': json_data.get('changeOfDirectors', None),
                    'consentAmalgamationOut': json_data.get('consentAmalgamationOut', None),
                    'consentContinuationOut': json_data.get('consentContinuationOut', None),
                    'continuationIn': json_data.get('continuationIn', None),
                    'continuationOut': json_data.get('continuationOut', None),
                    'courtOrder': json_data.get('courtOrder', None),
                    'dissolution': json_data.get('dissolution', None),
                    'incorporationApplication': json_data.get('incorporationApplication', None),
                    'putBackOff': json_data.get('putBackOff', None),
                    'putBackOn': json_data.get('putBackOn', None),
                    'registrarsNotation': json_data.get('registrarsNotation', None),
                    'registrarsOrder': json_data.get('registrarsOrder', None),
                    'restoration': json_data.get('restoration', None),
                    'specialResolution': json_data.get('specialResolution', None),
                    'transition': json_data.get('transition', None),
                }

            # Filter out null-values in the filing_list dictionary
            filing_list = {k: v for k, v in filing_list.items() if v}
            try:
                # get db connection and start a session, in case we need to roll back
                con = DB.connection
                con.begin()

                # No filing will be created for administrative dissolution. Create an event and update corp state.
                if (
                    'dissolution' in filing_list and
                    (filing_sub_type := Filing.get_filing_sub_type('dissolution', filing_list['dissolution']))
                    in ['administrative', 'involuntary']
                ):
                    if legal_type == Business.TypeCodes.COOP.value:
                        raise GenericException(
                            f'{filing_sub_type} dissolution of COOP is not implemented!',
                            HTTPStatus.NOT_IMPLEMENTED)

                    filing_dt = convert_to_pacific_time(json_data['header']['date'])
                    if filing_sub_type == 'administrative':
                        event_id = Filing.add_administrative_dissolution_event(con, identifier, filing_dt)
                    else:
                        event_id = Filing.add_involuntary_dissolution_event(con, identifier,
                                                                            filing_dt, filing_list['dissolution'])
                    con.commit()
                    return jsonify({
                        'filing': {
                            'header': {'colinIds': [event_id]}
                        }
                    }), HTTPStatus.CREATED

                # filing will not be created for Limited restoration expiration-Put back off (make business Historical)
                # Create an event and update corp state.
                if ('putBackOff' in filing_list and json_data['header']['hideInLedger'] is True):
                    filing_dt = convert_to_pacific_time(json_data['header']['date'])
                    event_id = Filing.add_limited_restoration_expiration_event(con, identifier, filing_dt)

                    con.commit()
                    return jsonify({
                        'filing': {
                            'header': {'colinIds': [event_id]}
                        }
                    }), HTTPStatus.CREATED

                filings_added = FilingInfo._add_filings(con, json_data, filing_list, identifier, lear_identifier)

                # success! commit the db changes
                con.commit()
                return jsonify({
                    'filing': {
                        'header': {'colinIds': [filing['event_id'] for filing in filings_added]}
                    }
                }), HTTPStatus.CREATED

            except Exception as db_err:
                current_app.logger.error('failed to file - rolling back partial db changes.')
                if con:
                    con.rollback()
                raise db_err

        except Exception as err:  # pylint: disable=broad-except; want to catch all errors
            # general catch-all exception
            current_app.logger.error(err.with_traceback(None))
            return jsonify({
                'message': f'Error when trying to file for business {identifier}',
                'error': str(err)
            }), HTTPStatus.INTERNAL_SERVER_ERROR

    @staticmethod
    def _add_filings(con, json_data: dict, filing_list: list, identifier: str, lear_identifier: str) -> list:
        """Process all parts of the filing."""
        filings_added = []
        for filing_type in filing_list:
            filing = Filing()
            filing.header = json_data['header']
            filing.filing_date = convert_to_pacific_time(filing.header['date'])
            filing.filing_type = filing_type
            filing_body = filing_list[filing_type]
            filing.filing_sub_type = Filing.get_filing_sub_type(filing_type, filing_body)
            filing.body = filing_body
            if filing.header['isFutureEffective']:
                # get utc lear effective date and convert to pacific time for insert into oracle
                filing.effective_date = convert_to_pacific_time(filing.header['learEffectiveDate'])
            else:
                filing.effective_date = filing.filing_date

            if filing_type in ['amalgamationApplication', 'continuationIn', 'incorporationApplication']:
                filing.business = Business.create_corporation(con, json_data)
            else:
                filing.business = Business.find_by_identifier(identifier, con=con)
            # add the new filing
            if filing_type == 'correction':
                filings_added.extend(Filing.add_correction_filings(con, filing))
            else:
                event_id = Filing.add_filing(con, filing, lear_identifier)
                filings_added.append({'event_id': event_id,
                                      'filing_type': filing_type,
                                      'filing_sub_type': filing.filing_sub_type})
        return filings_added


@cors_preflight('POST')
@API.route('/<string:legal_type>/<string:identifier>/filings/reminder')
# pylint: disable=too-few-public-methods
class UpdateARStatus(Resource):
    """Update the corporation and set_ar_to_no tables after a AR Reminder email is sent."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def post(identifier, **kwargs):
        """Trigger cleaning up data in Colin for the corporation after a Business AR Reminder email is sent."""
        # pylint: disable=unused-argument
        try:
            with DB.connection as con:
                with con.cursor() as cursor:
                    # First, check if the send_ar_ind flag is 'Y' for the given corporation
                    check_flag_query = """
                        SELECT send_ar_ind
                        FROM corporation
                        WHERE corp_num = :identifier
                    """
                    cursor.execute(check_flag_query, {'identifier': identifier})
                    result = cursor.fetchone()

                    # Return an error if corporation is not found or if the flag is already set to 'N'
                    if not result:
                        current_app.logger.warning(f'Corporation with identifier {identifier} not found.')
                        return jsonify(
                            {'message': f'Corporation with identifier {identifier} not found.'}
                        ), HTTPStatus.NOT_FOUND
                    set_ar_ind_flag = result[0].strip()
                    if set_ar_ind_flag != 'Y':
                        current_app.logger.warning(
                            f'send_ar_ind for corporation {identifier} is not Y. Current value: {set_ar_ind_flag}'
                        )
                        return jsonify(
                            {'message': f'send_ar_ind for corporation {identifier} must be Y.'}
                        ), HTTPStatus.BAD_REQUEST

                    # Update the send_ar_ind flag to 'N' in the corporation table
                    update_corporation_query = """
                        UPDATE corporation
                        SET send_ar_ind = 'N'
                        WHERE corp_num = :identifier
                    """
                    cursor.execute(update_corporation_query, {'identifier': identifier})

                    # Insert the corporation into the set_ar_to_no table with a previous value of 'Y'
                    insert_ar_to_no_query = """
                        INSERT INTO set_ar_to_no (corp_num, previous_value, update_date)
                        VALUES (:identifier, 'Y', CURRENT_TIMESTAMP)
                    """
                    cursor.execute(insert_ar_to_no_query, {'identifier': identifier})

                    # Commit the transaction
                    con.commit()
                    current_app.logger.info(f'Successfully updated AR status for corporation {identifier}.')
                    return jsonify({'message': f'AR status updated for corporation {identifier}.'}), HTTPStatus.OK

        except Exception as err:  # pylint: disable=broad-except
            current_app.logger.error(f'Error updating AR status for {identifier}: {str(err)}')
            return jsonify({'message': 'Error updating AR status.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@cors_preflight('DELETE')
@API.route('/<string:legal_type>/<string:identifier>/filings/reminder')
# pylint: disable=too-few-public-methods
class DeleteARPrompt(Resource):
    """Delete AR Prompt for corporation."""

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_roles([COLIN_SVC_ROLE])
    def delete(identifier, **kwargs):
        """Clean up data in Colin for the corporation."""
        # pylint: disable=unused-argument
        try:
            with DB.connection as con:
                with con.cursor() as cursor:
                    # Delete from AR prompt for the given corporation
                    delete_ar_prompt = """
                        DELETE FROM AR_PROMPT
                        WHERE corp_num = :identifier
                    """
                    cursor.execute(delete_ar_prompt, {'identifier': identifier})
                    # Commit the transaction
                    con.commit()
                    current_app.logger.info(f'Successfully deleted AR prompt for corporation {identifier}.')
                    return jsonify({'message': f'AR prompt deleted for corporation {identifier}.'}), HTTPStatus.OK

        except Exception as err:  # pylint: disable=broad-except
            current_app.logger.error(f'Error Deleteing AR status for {identifier}: {str(err)}')
            return jsonify({'message': 'Error Deleteing AR status.'}), HTTPStatus.INTERNAL_SERVER_ERROR
