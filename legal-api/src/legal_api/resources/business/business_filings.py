# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Searching on a business entity.

Provides all the search and retrieval from the business entity datastore.
"""
import datetime
from http import HTTPStatus
from typing import Tuple

import requests  # noqa: I001; grouping out of order to make both pylint & isort happy
from requests import exceptions  # noqa: I001; grouping out of order to make both pylint & isort happy
from flask import current_app, g, jsonify, request
from flask_restplus import Resource, cors
from werkzeug.local import LocalProxy

from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing, User, db
from legal_api.schemas import rsbc_schemas
from legal_api.services.authz import authorized
from legal_api.utils.auth import jwt
from legal_api.utils.util import cors_preflight

from .api_namespace import API
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


@cors_preflight('GET, POST, PUT, DELETE')
@API.route('/<string:identifier>/filings', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@API.route('/<string:identifier>/filings/<int:filing_id>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
class ListFilingResource(Resource):
    """Business Filings service."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(identifier, filing_id=None):
        """Return a JSON object with meta information about the Service."""
        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify({'message': f'{identifier} not found'}), HTTPStatus.NOT_FOUND

        if filing_id:
            rv = db.session.query(Business, Filing). \
                filter(Business.id == Filing.business_id).\
                filter(Business.identifier == identifier).\
                filter(Filing.id == filing_id).\
                one_or_none()
            if not rv:
                return jsonify({'message': f'{identifier} no filings found'}), HTTPStatus.NOT_FOUND

            return jsonify(rv[1].json)

        rv = []
        filings = business.filings.all()
        for filing in filings:
            rv.append(filing.json)

        return jsonify(filings=rv)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def post(identifier, filing_id=None):
        """Create a new filing for the business."""
        return ListFilingResource.put(identifier, filing_id)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def put(identifier, filing_id):
        """Modify an incomplete filing for the business."""
        # basic checks
        error = ListFilingResource._put_basic_checks(identifier, filing_id, request)
        if error:
            return jsonify(error[0]), error[1]

        # check authorization
        if not authorized(identifier, jwt):
            return jsonify({'message':
                            f'You are not authorized to submit a filing for {identifier}.'}), \
                HTTPStatus.UNAUTHORIZED

        # validate filing
        only_validate = request.args.get('only_validate', None)
        err_msg, err_code = ListFilingResource._validate_filing_json(request)
        if err_code != HTTPStatus.OK \
                or (only_validate and only_validate == 'true'):
            msg = {'errors': err_msg} if (err_code != HTTPStatus.OK) else err_msg
            return jsonify(msg), err_code

        # save filing
        user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
        business, filing, err_msg, err_code = ListFilingResource._save_filing(request, identifier, user, filing_id)
        if err_code:
            return jsonify(err_msg), err_code

        # create invoice ??
        draft = request.args.get('draft', None)
        if not draft or draft.lower() != 'true':
            err_msg, err_code = ListFilingResource._create_invoice(business, filing)
            if err_code:
                return jsonify(err_msg), err_code

        # all done
        return jsonify(filing.json),\
            (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)

    @staticmethod
    def _put_basic_checks(identifier, filing_id, client_request) -> Tuple[dict, int]:
        """Perform basic checks to ensure put can do something."""
        json_input = client_request.get_json()
        if not json_input:
            return ({'message':
                     f'No filing json data in body of post for {identifier}.'},
                    HTTPStatus.BAD_REQUEST)

        if filing_id and client_request.method != 'PUT':  # checked since we're overlaying routes
            return ({'message':
                     f'Illegal to attempt to create a new filing over an existing filing for {identifier}.'},
                    HTTPStatus.FORBIDDEN)

        return None

    @staticmethod
    def _save_filing(client_request: LocalProxy,
                     business_identifier: str,
                     user: User,
                     filing_id: int) \
            -> Tuple[Business, Filing, dict, int]:
        """Save the filing to the ledger.

        If not successful, a dict of errors is returned.

        Returns: {
            Business: business model object found for the identifier provided
            Filing: filing model object for the submitted filing
            dict: a dict of errors
            int: the HTTPStatus error code
        }
        """
        json_input = client_request.get_json()
        if not json_input:
            return None, None, {'message':
                                f'No filing json data in body of post for {business_identifier}.'}, \
                HTTPStatus.BAD_REQUEST

        business = Business.find_by_identifier(business_identifier)
        if not business:
            return None, None, {'message':
                                f'{business_identifier} not found'}, \
                HTTPStatus.NOT_FOUND

        if client_request.method == 'PUT':
            rv = db.session.query(Business, Filing). \
                filter(Business.id == Filing.business_id). \
                filter(Business.identifier == business_identifier). \
                filter(Filing.id == filing_id). \
                one_or_none()
            if not rv:
                return None, None, {'message':
                                    f'{business_identifier} no filings found'}, \
                    HTTPStatus.NOT_FOUND
            filing = rv[1]
        else:
            filing = Filing()
            filing.business_id = business.id

        try:
            filing.submitter_id = user.id
            filing.filing_date = datetime.datetime.utcnow()
            filing.filing_json = json_input
            filing.save()
        except BusinessException as err:
            return None, None, {'message': err.error}, err.status_code

        return business, filing, None, None

    @staticmethod
    def _validate_filing_json(client_request: LocalProxy) -> Tuple[dict, int]:
        """Assert that the json is a valid filing.

        Returns: {
            dict: a dict, success message or array of errors
            int: the HTTPStatus error code
        }
        """
        valid, err = rsbc_schemas.validate(client_request.get_json(), 'filing')

        if valid:
            return {'message': 'Filing is valid'}, HTTPStatus.OK

        errors = []
        for error in err:
            errors.append({'path': '/'.join(error.path), 'error': error.message})
        return errors, HTTPStatus.BAD_REQUEST

    @staticmethod
    def _create_invoice(business: Business,
                        filing: Filing) \
            -> Tuple[int, dict, int]:
        """Create the invoice for the filing submission.

        Returns: {
            int: the paymentToken (id), or None
            dict: a dict of errors, or None
            int: the HTTPStatus error code, or None
        }
        """
        payment_svc_url = current_app.config.get('PAYMENT_SVC_URL')

        filing_types = []
        for k in filing.filing_json['filing'].keys():
            if Filing.FILINGS.get(k, None):
                filing_types.append({'filing_type_code': Filing.FILINGS[k].get('code')})

        mailing_address = business.business_mailing_address.one_or_none()

        payload = {
            'payment_info': {'method_of_payment': 'CC'},
            'business_info': {
                'business_identifier': f'{business.identifier}',
                'corp_type': f'{business.identifier[:-7]}',
                'business_name': f'{business.legal_name}',
                'contact_info': {'city': mailing_address.city,
                                 'postal_code': mailing_address.postal_code,
                                 'province': mailing_address.region,
                                 'address_line_1': mailing_address.street,
                                 'country': mailing_address.country}
            },
            'filing_info': {
                'filing_types': filing_types
            }
        }

        try:
            rv = requests.post(payment_svc_url, json=payload)
        except exceptions.ConnectionError as err:
            current_app.logger.error(f'Payment connection failure for {business.identifier}: filing:{filing.id}', err)
            return {'message': 'unable to create invoice for payment.'}, HTTPStatus.PAYMENT_REQUIRED

        pid = rv.json().get('id')
        filing.payment_token = pid
        filing.save()
        return None, None
