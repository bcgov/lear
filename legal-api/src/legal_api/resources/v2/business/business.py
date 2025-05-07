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
"""Searching on a business entity.

Provides all the search and retrieval from the business entity datastore.
"""
from contextlib import suppress
from http import HTTPStatus

from flask import current_app, g, jsonify, request
from flask_babel import _ as babel  # noqa: N813
from flask_cors import cross_origin

from legal_api.core import Filing as CoreFiling
from legal_api.models import Business, Filing, RegistrationBootstrap
from legal_api.resources.v2.business.business_filings import saving_filings
from legal_api.services import (  # noqa: I001;
    ACCOUNT_IDENTITY,
    SYSTEM_ROLE,
    AccountService,
    RegistrationBootstrapService,
    check_warnings,
    flags,
)  # noqa: I001;
from legal_api.services.authz import authorized, get_allowable_actions, get_allowed, get_could_files
from legal_api.services.search_service import AffiliationSearchDetails, BusinessSearchService
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route('/<string:identifier>', methods=['GET'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_businesses(identifier: str):
    """Return a JSON object with meta information about the Service."""
    if identifier.startswith('T'):
        return {'message': babel('No information on temp registrations.')}, 200

    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

    # getting all business info is expensive so returning the slim version is desirable for some flows
    # - (i.e. business/person search updates)
    if str(request.args.get('slim', None)).lower() == 'true':
        business_json = business.json(slim=True)
        # need to add the alternateNames array here because it is not a part of slim JSON
        business_json['alternateNames'] = business.get_alternate_names()

        return jsonify(business=business_json)

    # check authorization if required
    if flags.is_on('enable-auth-v2-business') and not authorized(identifier, jwt, action=['view']):
        current_app.logger.warning(
            'Unauthorized request for business: %s, from username: %s, accountId: %s, app-name: %s',
            identifier,
            g.jwt_oidc_token_info.get('preferred_username'),
            request.args.get('account'),
            request.headers.get('app-name'))
        return jsonify({'message':
                        f'You are not authorized to view business {identifier}.'}), \
            HTTPStatus.UNAUTHORIZED

    warnings = check_warnings(business)
    # TODO remove complianceWarnings line when UI has been integrated to use warnings instead of complianceWarnings
    business.compliance_warnings = warnings
    business.warnings = warnings

    allowable_actions = get_allowable_actions(jwt, business)
    business.allowable_actions = allowable_actions

    business_json = business.json()

    recent_filing_json = CoreFiling.get_most_recent_filing_json(business.id, None, jwt)
    if recent_filing_json:
        business_json['submitter'] = recent_filing_json['filing']['header']['submitter']

    allowed_filings = str(request.args.get('allowed_filings', None)).lower() == 'true'
    if allowed_filings:
        business_json['allowedFilings'] = get_allowed(business.state, business.legal_type, jwt)

    q_account = request.args.get('account')
    current_app.logger.info('account info request, for account: %s', q_account)
    if q_account and jwt.has_one_of_roles([SYSTEM_ROLE, ACCOUNT_IDENTITY]):
        account_response = AccountService.get_account_by_affiliated_identifier(identifier)
        current_app.logger.info('VALID account request, for accountId: %s, by: %s, jwt: %s, for org account: %s',
                                q_account,
                                g.jwt_oidc_token_info.get('preferred_username'),
                                g.jwt_oidc_token_info,
                                account_response)
        if orgs := account_response.get('orgs'):
            # A business can be affiliated in multiple accounts (in user account as well as in gov staff account's)
            # AccountService.get_account_by_affiliated_identifier will fetch all of it
            # check one of it has `q_account`
            if any(str(org.get('id')) == q_account for org in orgs):
                business_json['accountId'] = q_account

    return jsonify(business=business_json)


@bp.route('', methods=['POST'])
@cross_origin(origin='*')
@jwt.requires_auth
def post_businesses():
    """Create a valid filing, else error out."""
    json_input = request.get_json()
    try:
        filing_account_id = json_input['filing']['header']['accountId']
        filing_type = json_input['filing']['header']['name']
        if filing_type not in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            raise TypeError
    except (TypeError, KeyError):
        return {'error': babel('Requires a valid filing.')}, HTTPStatus.BAD_REQUEST

    filing_title = filing_type
    with suppress(KeyError):
        if filing_sub_type := Filing.get_filings_sub_type(filing_type, json_input):
            filing_title = Filing.FILINGS[filing_type][filing_sub_type]['title']
        else:
            filing_title = Filing.FILINGS[filing_type]['title']

    # @TODO rollback bootstrap if there is A failure, awaiting changes in the affiliation service
    bootstrap = RegistrationBootstrapService.create_bootstrap(filing_account_id)
    if not isinstance(bootstrap, RegistrationBootstrap):
        return {'error': babel('Unable to create {0} Filing.'.format(filing_title))}, \
            HTTPStatus.SERVICE_UNAVAILABLE

    try:
        business_name = json_input['filing'][filing_type]['nameRequest']['nrNumber']
    except KeyError:
        business_name = bootstrap.identifier

    legal_type = json_input['filing'][filing_type]['nameRequest']['legalType']
    corp_type_code = Filing.FILINGS[filing_type]['temporaryCorpTypeCode']
    rv = RegistrationBootstrapService.register_bootstrap(bootstrap,
                                                         business_name,
                                                         corp_type_code=corp_type_code,
                                                         corp_sub_type_code=legal_type)
    if not isinstance(rv, HTTPStatus):
        with suppress(Exception):
            bootstrap.delete()
        return {'error': babel('Unable to create {0} Filing.'.format(filing_title))}, \
            HTTPStatus.SERVICE_UNAVAILABLE

    return saving_filings(identifier=bootstrap.identifier)  # pylint: disable=no-value-for-parameter


@bp.route('/search', methods=['POST'])
@cross_origin(origin='*')
@jwt.requires_roles([SYSTEM_ROLE])
def search_businesses():
    """Return the list of businesses and draft businesses."""
    try:
        json_input = request.get_json()
        identifiers = json_input.get('identifiers', None)
        temp_identifiers = []
        business_identifiers = []
        if not identifiers or not isinstance(identifiers, list):
            return {'message': "Expected a list of 1 or more for '/identifiers'"}, HTTPStatus.BAD_REQUEST

        for identifier in identifiers:
            if identifier.startswith('T'):
                temp_identifiers.append(identifier)
            else:
                business_identifiers.append(identifier)
        search_filters = AffiliationSearchDetails.from_request_args(json_input)
        bus_results = BusinessSearchService.get_search_filtered_businesses_results(
            business_json=json_input,
            identifiers=business_identifiers,
            search_filters=search_filters)
        draft_results = BusinessSearchService.get_search_filtered_filings_results(
            business_json=json_input,
            identifiers=temp_identifiers,
            search_filters=search_filters)

        return jsonify({'businessEntities': bus_results, 'draftEntities': draft_results}), HTTPStatus.OK
    except Exception as err:
        current_app.logger.info(err)
        current_app.logger.error('Error searching over business information for: %s', identifiers)
        return {'error': 'Unable to retrieve businesses.'}, HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route('/allowable/<string:business_type>/<string:business_state>', methods=['GET'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_allowable_for_business_type(business_type: str, business_state: str):
    """Return a JSON object with information about what a user could theoretically file for a business type."""
    business_state = business_state.upper()
    business_type = business_type.upper()

    bs_state = getattr(Business.State, business_state, False)
    if not bs_state:
        return {'message': babel('Invalid business state.')}, HTTPStatus.BAD_REQUEST

    try:
        _ = Business.LegalTypes(business_type)
    except ValueError:
        return {'message': babel('Invalid business type.')}, HTTPStatus.BAD_REQUEST

    could_file = get_could_files(jwt, business_type, business_state)

    return jsonify(couldFile=could_file)
