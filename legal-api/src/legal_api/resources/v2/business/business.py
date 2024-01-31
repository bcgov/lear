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
from sqlalchemy import and_

from legal_api.core import Filing as CoreFiling
from legal_api.models import Business, Filing, RegistrationBootstrap, db
from legal_api.resources.v2.business.business_filings import saving_filings
from legal_api.services import (  # noqa: I001;
    ACCOUNT_IDENTITY,
    SYSTEM_ROLE,
    AccountService,
    RegistrationBootstrapService,
    check_warnings,
)  # noqa: I001;
from legal_api.services.authz import get_allowable_actions, get_allowed
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
    # check authorization -- need to implement workaround for business search users before using this
    # if not authorized(identifier, jwt, action=['view']):
    #     return jsonify({'message':
    #                     f'You are not authorized to view business {identifier}.'}), \
    #         HTTPStatus.UNAUTHORIZED

    # getting all business info is expensive so returning the slim version is desirable for some flows
    # - (i.e. business search update)
    if str(request.args.get('slim', None)).lower() == 'true':
        return jsonify(business=business.json(slim=True))

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
        business_json['lastModified'] = recent_filing_json['filing']['header']['date']

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
    valid_filing_types = [
        Filing.FILINGS['incorporationApplication']['name'],
        Filing.FILINGS['registration']['name'],
        Filing.FILINGS['amalgamationApplication']['name']
    ]

    try:
        filing_account_id = json_input['filing']['header']['accountId']
        filing_type = json_input['filing']['header']['name']
        if filing_type not in valid_filing_types:
            raise TypeError
    except (TypeError, KeyError):
        return {'error': babel('Requires a valid filing.')}, HTTPStatus.BAD_REQUEST

    # @TODO rollback bootstrap if there is A failure, awaiting changes in the affiliation service
    bootstrap = RegistrationBootstrapService.create_bootstrap(filing_account_id)
    if not isinstance(bootstrap, RegistrationBootstrap):
        if filing_sub_type := Filing.get_filings_sub_type(filing_type, json_input):
            title = Filing.FILINGS[filing_type][filing_sub_type]['title']
        else:
            title = Filing.FILINGS[filing_type]['title']
        return {'error': babel('Unable to create {0} Filing.'.format(title))}, \
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
        return {'error': babel('Unable to create {0} Filing.'.format(Filing.FILINGS[filing_type]['title']))}, \
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
        if not identifiers or not isinstance(identifiers, list):
            return {'message': "Expected a list of 1 or more for '/identifiers'"}, HTTPStatus.BAD_REQUEST

        # base business query
        bus_query = db.session.query(Business).filter(Business._identifier.in_(identifiers))  # noqa: E501; pylint: disable=protected-access

        # base filings query (for draft incorporation/registration filings -- treated as 'draft' business in auth-web)
        draft_query = db.session.query(Filing).filter(
            and_(Filing.temp_reg.in_(identifiers), Filing.business_id.is_(None)))

        # parse results
        bus_results = [x.json(slim=True) for x in bus_query.all()]
        draft_results = [
            {
                'identifier': x.temp_reg,
                'legalType': x.json_legal_type,
                **({'nrNumber': x.json_nr} if x.json_nr else {}),
                **({'legalName': x.filing_json.get('filing', {})
                    .get(x.filing_type).get('nameRequest', {})
                    .get('legalName')}
                   if x.filing_type == 'amalgamationApplication' else {})
            } for x in draft_query.all()]

        return jsonify({'businessEntities': bus_results, 'draftEntities': draft_results}), HTTPStatus.OK
    except Exception as err:
        current_app.logger.info(err)
        current_app.logger.error('Error searching over business information for: %s', identifiers)
        return {'error': 'Unable to retrieve businesses.'}, HTTPStatus.INTERNAL_SERVER_ERROR
