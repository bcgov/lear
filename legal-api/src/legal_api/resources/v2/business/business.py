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
from datetime import datetime, timezone
from http import HTTPStatus

from flask import current_app, g, jsonify, request
from flask_babel import _ as babel  # noqa: N813
from flask_cors import cross_origin
from sqlalchemy import and_

from legal_api.core import Filing as CoreFiling
from legal_api.models import Address, Business, Filing, Office, RegistrationBootstrap, db
from legal_api.models.db import VersioningProxy
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
from sql_versioning.versioned_history import enable_versioning, disable_versioning
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
    # check authorization -- need to implement workaround for business search users before using this #22143
    # if not authorized(identifier, jwt, action=['view']):
    #     return jsonify({'message':
    #                     f'You are not authorized to view business {identifier}.'}), \
    #         HTTPStatus.UNAUTHORIZED

    # getting all business info is expensive so returning the slim version is desirable for some flows
    # - (i.e. business/person search updates)
    if str(request.args.get('slim', None)).lower() == 'true':
        business_json = business.json(slim=True)
        # need to add the alternateNames array here because it is not a part of slim JSON
        business_json['alternateNames'] = business.get_alternate_names()
        return jsonify(business=business_json)

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
        if not identifiers or not isinstance(identifiers, list):
            return {'message': "Expected a list of 1 or more for '/identifiers'"}, HTTPStatus.BAD_REQUEST

        # base business query
        bus_query = db.session.query(Business).filter(Business._identifier.in_(identifiers))  # noqa: E501; pylint: disable=protected-access

        # base filings query (for draft incorporation/registration filings -- treated as 'draft' business in auth-web)
        draft_query = db.session.query(Filing).filter(
            and_(Filing.temp_reg.in_(identifiers), Filing.business_id.is_(None)))

        bus_results = []

        # SBC-AUTH only uses alternateNames for SP and GP at the moment
        # we are not returning alternateNames for non-firms due to performance issues
        for business in bus_query.all():
            business_json = business.json(slim=True)
            # add alternateNames array to slim json only to firms
            if business.legal_type in (Business.LegalTypes.SOLE_PROP, Business.LegalTypes.PARTNERSHIP):
                business_json['alternateNames'] = business.get_alternate_names()
            bus_results.append(business_json)

        draft_results = []
        for draft_dao in draft_query.all():
            draft = {
                'identifier': draft_dao.temp_reg,  # Temporary registration number of the draft entity
                'legalType': draft_dao.json_legal_type,  # Legal type of the draft entity
                'draftType': Filing.FILINGS.get(draft_dao.filing_type, {}).get('temporaryCorpTypeCode'),
                'draftStatus': draft_dao.status
            }

            if (draft_dao.status in [Filing.Status.PAID.value, Filing.Status.APPROVED.value] and
                    draft_dao.effective_date and draft_dao.effective_date > datetime.now(timezone.utc)):
                draft['effectiveDate'] = draft_dao.effective_date.isoformat()

            if draft_dao.json_nr:
                draft['nrNumber'] = draft_dao.json_nr  # Name request number, if available
            # Retrieves the legal name from the filing JSON. Defaults to None if not found.
            draft['legalName'] = (draft_dao.filing_json.get('filing', {})
                                  .get(draft_dao.filing_type, {})
                                  .get('nameRequest', {})
                                  .get('legalName'))

            if draft['legalName'] is None:
                # Fallback to a generic legal name based on the legal type if no specific legal name is found
                draft['legalName'] = (Business.BUSINESSES
                                      .get(draft_dao.json_legal_type, {})
                                      .get('numberedDescription'))
            draft_results.append(draft)

        return jsonify({'businessEntities': bus_results, 'draftEntities': draft_results}), HTTPStatus.OK
    except Exception as err:
        current_app.logger.info(err)
        current_app.logger.error('Error searching over business information for: %s', identifiers)
        return {'error': 'Unable to retrieve businesses.'}, HTTPStatus.INTERNAL_SERVER_ERROR


# experimental debugging endpoints
@bp.route('/db_versioning_test/update', methods=['GET'])
@cross_origin(origin='*')
def db_versioning_test():
    """Return a JSON object with meta information about the Service.
    
    Update a business.
    """
    identifier = 'FM0385546'
    business = Business.find_by_identifier(identifier)
    business.admin_freeze = not business.admin_freeze
    business.save()
    business = Business.find_by_identifier(identifier)
    return jsonify({'success': True, 'admin_freeze': business.admin_freeze}), HTTPStatus.OK


@bp.route('/db_versioning_test/updates', methods=['GET'])
@cross_origin(origin='*')
def db_versioning_test_updates():
    """Return a JSON object with meta information about the Service.
    
    Update a business and FK related address. (business -> office -> address)
    """
    identifier = 'FM0385546'
    business = Business.find_by_identifier(identifier)
    business.admin_freeze = not business.admin_freeze
    mailing_address = business.mailing_address.one_or_none()
    if mailing_address:
        mailing_address.delivery_instructions = 'HJ Test' if not mailing_address.delivery_instructions else ''
    else:
        print(f'Skip updating mailing address for Business(id={business.id})')
    business.save()
    business = Business.find_by_identifier(identifier)
    return jsonify({'success': True, 'id': business.id, 'admin_freeze': business.admin_freeze, 'address_id': mailing_address.id, 'delivery_instructions': mailing_address.delivery_instructions}), HTTPStatus.OK


@bp.route('/db_versioning_test/insert', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_insert():
    """Return a JSON object with meta information about the Service.

    Create and insert a dummy business.
    """
    identifier = 'BC0000001'
    business = Business(identifier=identifier, legal_name='HJ Test db versioning')
    business.save()
    return jsonify({'success': True, 'id': business.id})


@bp.route('/db_versioning_test/inserts', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_inserts():
    """Return a JSON object with meta information about the Service.

    Create and insert a dummy business with FK related offices, addresses.
    """
    identifier = 'BC0000001'
    business = Business(identifier=identifier, legal_name='HJ Test db versioning')
    address=Address(
        city='HJ TEST City',
        street='HJ Test Street',
        postal_code='X1X1X1',
        country='CA',
        region='BC',
        address_type=Address.MAILING
    )
    office=Office(office_type='registeredOffice')
    office.addresses.append(address)
    business.offices.append(office)
    business.save()
    return jsonify({'success': True, 'business_id': business.id, 'office_id': office.id, 'address_id': address.id})


@bp.route('/db_versioning_test/delete/<int:business_id>', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_delete(business_id):
    """Return a JSON object with meta information about the Service.

    Delete a dummy business.
    Need a dummy business without FK related records to test this endpoint.
    """
    business = Business.find_by_internal_id(business_id)
    db.session.delete(business)
    db.session.commit()
    return jsonify({'success': True, 'id': business_id})


@bp.route('/db_versioning_test/deletes/<int:business_id>', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_deletes(business_id):
    """Return a JSON object with meta information about the Service.

    Delete a dummy business with FK related offices, addresses.
    Need a dummy business with FK related records to test this endpoint.
    """
    business = Business.find_by_internal_id(business_id)
    db.session.delete(business)
    db.session.commit()
    return jsonify({'success': True, 'id': business_id})


@bp.route('/db_versioning_test/flush', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_flush():
    """Return a JSON object with meta information about the Service.

    Test flush + add + flush/commit scenario. The transaction_id should keep the same.
    """
    identifier_1 = 'BC0000001'
    business_1 = Business(identifier=identifier_1, legal_name='HJ Test db versioning-1')
    db.session.add(business_1)
    db.session.flush()
    identifier_2 = 'BC0000002'
    business_2 = Business(identifier=identifier_2, legal_name='HJ Test db versioning-2')
    db.session.add(business_2)
    db.session.commit()

    return jsonify({'success': True, 'id_1': business_1.id, 'id_2': business_2.id})


@bp.route('/db_versioning_test/query/<int:business_id>/<int:transaction_id>', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_query(business_id, transaction_id):
    """Return a JSON object of versioned business data.
    """
    try:
        session = db.session()
        business_version = VersioningProxy.version_class(session, Business)
        print(f'Primary Key={business_version.__table__.primary_key}')

        query = session.query(business_version)\
            .filter(business_version.id == business_id)\
            .filter(business_version.transaction_id <= transaction_id)

        business_list = query.all()

        return jsonify({'success': True, 'found': len(business_list)})
    except Exception as e:
        print(f'Error:{e}')
        return jsonify({'success': False})


@bp.route('/db_versioning_test/enable', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_enable():
    """Return a JSON object with meta information about the Service.

    Enable new versioning (Don't use it when two versionings are both enabled)
    """
    if not Business.is_enable:
        enable_versioning(db.session)

    return jsonify({'success': True, 'enable': Business.is_enable})


@bp.route('/db_versioning_test/disable', methods=['GET'])
@cross_origin(origins='*')
def db_versioning_test_disable():
    """Return a JSON object with meta information about the Service.

    Disable new versioning (Don't use it when two versionings are both enabled)
    """
    if Business.is_enable:
        disable_versioning(db.session)

    return jsonify({'success': True, 'enable': Business.is_enable})