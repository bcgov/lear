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
import datedelta
from flask import current_app, g, jsonify, request
from flask_babel import _
from flask_jwt_oidc import JwtManager
from flask_restplus import Resource, cors
from werkzeug.local import LocalProxy

import legal_api.reports
from legal_api.exceptions import BusinessException
from legal_api.models import Business, Filing, User, db
from legal_api.schemas import rsbc_schemas
from legal_api.services import COLIN_SVC_ROLE, STAFF_ROLE, authorized, queue
from legal_api.services.filings import validate
from legal_api.services.filings.utils import get_str
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
    @jwt.requires_auth
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

            if str(request.accept_mimetypes) == 'application/pdf':
                return legal_api.reports.get_pdf(rv[1])

            return jsonify(rv[1].json)

        # Does it make sense to get a PDF of all filings?
        if str(request.accept_mimetypes) == 'application/pdf':
            return jsonify({'message': _('Cannot return a single PDF of multiple filing submissions.')}),\
                HTTPStatus.NOT_ACCEPTABLE

        rv = []
        filings = Filing.get_filings_by_status(business.id, [Filing.Status.COMPLETED.value])
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
    def put(identifier, filing_id):  # pylint: disable=too-many-return-statements
        """Modify an incomplete filing for the business."""
        # basic checks
        err_msg, err_code = ListFilingResource._put_basic_checks(identifier, filing_id, request)
        if err_msg:
            return jsonify({'errors': [err_msg, ]}), err_code
        json_input = request.get_json()

        # check authorization
        if not authorized(identifier, jwt, action=['edit']):
            return jsonify({'message':
                            f'You are not authorized to submit a filing for {identifier}.'}), \
                HTTPStatus.UNAUTHORIZED
        draft = (request.args.get('draft', None).lower() == 'true') \
            if request.args.get('draft', None) else False
        only_validate = (request.args.get('only_validate', None).lower() == 'true') \
            if request.args.get('only_validate', None) else False
        # validate filing
        if not draft and not ListFilingResource._is_before_epoch_filing(json_input,
                                                                        Business.find_by_identifier(identifier)):
            business = Business.find_by_identifier(identifier)
            err = validate(business, json_input)
            # err_msg, err_code = ListFilingResource._validate_filing_json(request)
            if err or only_validate:
                if err:
                    json_input['errors'] = err.msg
                    return jsonify(json_input), err.code
                return jsonify(json_input), HTTPStatus.OK
        # save filing, if it's draft only then bail
        user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
        business, filing, err_msg, err_code = ListFilingResource._save_filing(request, identifier, user, filing_id)
        if err_msg or draft:
            reply = filing.json if filing else json_input
            reply['errors'] = [err_msg, ]
            return jsonify(reply), err_code or \
                (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)

        # if filing is from COLIN, place on queue and return
        if jwt.validate_roles([COLIN_SVC_ROLE]):
            err_msg, err_code = ListFilingResource._process_colin_filing(identifier, filing, business)
            return jsonify(err_msg), err_code

        # create invoice ??
        if not draft:
            filing_types = ListFilingResource._get_filing_types(filing.filing_json)
            err_msg, err_code = ListFilingResource._create_invoice(business, filing, filing_types, jwt)
            if err_code:
                reply = filing.json
                reply['errors'] = [err_msg, ]
                return jsonify(reply), err_code
            ListFilingResource._set_effective_date(business, filing)
        # all done
        return jsonify(filing.json),\
            (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def delete(identifier, filing_id=None):
        """Delete a filing from the business."""
        if not filing_id:
            return ({'message':
                     _('No filing id provided for:') + identifier},
                    HTTPStatus.BAD_REQUEST)

        # check authorization
        if not authorized(identifier, jwt, action=['edit']):
            return jsonify({'message':
                            _('You are not authorized to delete a filing for:') + identifier}),\
                HTTPStatus.UNAUTHORIZED

        filing = Business.get_filing_by_id(identifier, filing_id)

        if not filing:
            return jsonify({'message':
                            _('Filing Not Found.')}), \
                HTTPStatus.NOT_FOUND

        try:
            filing.delete()
            return jsonify({'message':
                            _('Filing deleted.')}), \
                HTTPStatus.OK
        except BusinessException as err:
            return jsonify({'errors': [
                {'error': err.error},
            ]}), err.status_code

        return {}, HTTPStatus.NOT_IMPLEMENTED

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
                     f'Illegal to attempt to create a duplicate filing for {identifier}.'},
                    HTTPStatus.FORBIDDEN)

        return None, None

    @staticmethod
    def _is_before_epoch_filing(filing_json: str, business: Business):
        if not business or not filing_json:
            return False
        epoch_filing = Filing.get_filings_by_status(business_id=business.id, status=[Filing.Status.EPOCH.value])
        if len(epoch_filing) != 1:
            current_app.logger.error('Business:%s either none or too many epoch filings', business.identifier)
            return False
        filing_date = datetime.datetime.fromisoformat(
            filing_json['filing']['header']['date']).replace(tzinfo=datetime.timezone.utc)
        return filing_date < epoch_filing[0].filing_date

    @staticmethod
    def _process_colin_filing(identifier: str, filing: Filing, business: Business) -> Tuple[dict, int]:
        try:
            if not filing.colin_event_id:
                raise KeyError
            if not ListFilingResource._is_before_epoch_filing(filing.filing_json, business):
                payload = {'colinFiling': {'id': filing.colin_event_id}}
                queue.publish_json(payload)
            else:
                epoch_filing = Filing.get_filings_by_status(business_id=business.id, status=[Filing.Status.EPOCH.value])
                filing.transaction_id = epoch_filing[0].transaction_id
                filing.save()
            return {}, HTTPStatus.CREATED
        except KeyError:
            current_app.logger.error('Business:%s missing filing/header/colinId, unable to post to queue',
                                     identifier)
            return {'errors': {'message': 'missing filing/header/colinId'}}, HTTPStatus.BAD_REQUEST
        except Exception as err:  # pylint: disable=broad-except; final catch
            current_app.logger.error('Business:%s unable to post to queue, err=%s', identifier, err)
            return {'errors': {'message': 'unable to publish for post processing'}}, HTTPStatus.BAD_REQUEST

    @staticmethod
    def _save_filing(client_request: LocalProxy,
                     business_identifier: str,
                     user: User,
                     filing_id: int) -> Tuple[Business, Filing, dict, int]:
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
                                f'{business_identifier} not found'}, HTTPStatus.NOT_FOUND

        if client_request.method == 'PUT':
            rv = db.session.query(Business, Filing). \
                filter(Business.id == Filing.business_id). \
                filter(Business.identifier == business_identifier). \
                filter(Filing.id == filing_id). \
                one_or_none()
            if not rv:
                return None, None, {'message':
                                    f'{business_identifier} no filings found'}, HTTPStatus.NOT_FOUND
            filing = rv[1]
        else:
            filing = Filing()
            filing.business_id = business.id

        try:
            filing.submitter_id = user.id
            filing.filing_json = json_input
            if user.username == 'coops-updater-job':
                try:
                    filing.filing_date = datetime.datetime.fromisoformat(filing.filing_json['filing']['header']['date'])
                    filing.colin_event_id = filing.filing_json['filing']['header']['colinId']
                except KeyError:
                    current_app.logger.error('Business:%s missing filing/header values, unable to save',
                                             business.identifier)
                    return None, None, {'message': 'missing filing/header values'}, HTTPStatus.BAD_REQUEST
            else:
                filing.filing_date = datetime.datetime.utcnow()
            filing.save()
        except BusinessException as err:
            return None, None, {'error': err.error}, err.status_code

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
    def _get_filing_types(filing_json: dict):
        """Get the filing type fee codes for the filing.

        Returns: {
            list: a list, filing type fee codes in the filing
        }
        """
        filing_types = []
        for k in filing_json['filing'].keys():
            # check if changeOfDirectors is a free filing
            if k == 'changeOfDirectors':
                free = True
                free_changes = ['nameChanged', 'addressChanged']
                for director in filing_json['filing'][k].get('directors'):
                    # if changes other than name/address change then this is not a free filing
                    if not all(change in free_changes for change in director.get('actions', [])):
                        free = False
                        break
                filing_types.append({
                    'filingTypeCode': 'OTFDR' if free else Filing.FILINGS[k].get('code')
                })
            elif Filing.FILINGS.get(k, None):
                filing_types.append({'filingTypeCode': Filing.FILINGS[k].get('code')})
        return filing_types

    @staticmethod
    def _create_invoice(business: Business,
                        filing: Filing,
                        filing_types: list,
                        user_jwt: JwtManager) \
            -> Tuple[int, dict, int]:
        """Create the invoice for the filing submission.

        Returns: {
            int: the paymentToken (id), or None
            dict: a dict of errors, or None
            int: the HTTPStatus error code, or None
        }
        """
        payment_svc_url = current_app.config.get('PAYMENT_SVC_URL')
        mailing_address = business.mailing_address.one_or_none()

        payload = {
            'paymentInfo': {'methodOfPayment': 'CC'},
            'businessInfo': {
                'businessIdentifier': f'{business.identifier}',
                'corpType': f'{business.identifier[:-7]}',
                'businessName': f'{business.legal_name}',
                'contactInfo': {'city': mailing_address.city,
                                'postalCode': mailing_address.postal_code,
                                'province': mailing_address.region,
                                'addressLine1': mailing_address.street,
                                'country': mailing_address.country}
            },
            'filingInfo': {
                'filingTypes': filing_types
            }
        }

        if user_jwt.validate_roles([STAFF_ROLE]):
            routing_slip_number = get_str(filing.filing_json, 'filing/header/routingSlipNumber')
            if routing_slip_number:
                payload['accountInfo'] = {'routingSlip': routing_slip_number}
        try:
            token = user_jwt.get_token_auth_header()
            headers = {'Authorization': 'Bearer ' + token}
            rv = requests.post(url=payment_svc_url,
                               json=payload,
                               headers=headers,
                               timeout=20.0)
        except (exceptions.ConnectionError, exceptions.Timeout) as err:
            current_app.logger.error(f'Payment connection failure for {business.identifier}: filing:{filing.id}', err)
            return {'message': 'unable to create invoice for payment.'}, HTTPStatus.PAYMENT_REQUIRED

        if rv.status_code == HTTPStatus.OK or rv.status_code == HTTPStatus.CREATED:
            pid = rv.json().get('id')
            filing.payment_token = pid
            filing.save()
            return None, None
        return {'message': 'unable to create invoice for payment.'}, HTTPStatus.PAYMENT_REQUIRED

    @staticmethod
    def _set_effective_date(business: Business, filing: Filing):
        filing_type = filing.filing_json['filing']['header']['name']
        if business.legal_type != 'CP':
            if filing_type == 'changeOfAddress':
                effective_date = datetime.datetime.combine(datetime.date.today() + datedelta.datedelta(days=1), \
                    datetime.datetime.min.time())
                filing.filing_json['filing']['header']['futureEffectiveDate'] = effective_date
                filing.effective_date = effective_date
                filing.save()


@cors_preflight('GET, POST, PUT, PATCH, DELETE')
@API.route('/internal/filings', methods=['GET', 'OPTIONS'])
@API.route('/internal/filings/<string:status>', methods=['GET', 'OPTIONS'])
@API.route('/internal/filings/<int:filing_id>', methods=['PATCH', 'OPTIONS'])
class InternalFilings(Resource):
    """Internal Filings service for cron jobs."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(status=None):
        """Get filings to send to colin."""
        filings = []

        if status is None:
            pending_filings = Filing.get_completed_filings_for_colin()
        elif status == Filing.Status.PAID.value:
            pending_filings = Filing.get_all_filings_by_status(status)

        filings = [x.json for x in pending_filings]
        return jsonify(filings), HTTPStatus.OK

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def patch(filing_id):
        """Patch the colin_event_id for a filing."""
        # check authorization
        if not jwt.validate_roles([COLIN_SVC_ROLE]):
            return jsonify({'message': 'You are not authorized to update the colin id'}), HTTPStatus.UNAUTHORIZED

        json_input = request.get_json()
        if not json_input:
            return None, None, {'message': f'No filing json data in body of patch for {filing_id}.'}, \
                HTTPStatus.BAD_REQUEST

        colin_id = json_input['colinId']
        filing = Filing.find_by_id(filing_id)
        if not filing:
            return {'message': f'{filing_id} no filings found'}, HTTPStatus.NOT_FOUND
        try:
            filing.colin_event_id = colin_id
            filing.save()
        except BusinessException as err:
            return None, None, {'message': err.error}, err.status_code

        return jsonify(filing.json), HTTPStatus.ACCEPTED


@cors_preflight('GET, POST, PUT, PATCH, DELETE')
@API.route('/internal/filings/colin_id', methods=['GET', 'OPTIONS'])
@API.route('/internal/filings/colin_id/<int:colin_id>', methods=['GET', 'POST', 'OPTIONS'])
class ColinLastUpdate(Resource):
    """Endpoints for colin_last_update table."""

    @staticmethod
    @cors.crossdomain(origin='*')
    def get(colin_id=None):
        """Get the last colin id updated in legal."""
        if colin_id:
            query = db.session.execute(
                f"""
                select colin_event_id
                from filings
                where colin_event_id={colin_id}
                """
            )
            colin_id = query.fetchone()
            if not colin_id:
                return {'message': f'No colin ids found'}, HTTPStatus.NOT_FOUND

            return {'colinId': colin_id[0]}, HTTPStatus.OK

        query = db.session.execute(
            """
            select last_event_id from colin_last_update
            order by id desc
            """
        )
        last_event_id = query.fetchone()
        if not last_event_id or not last_event_id[0]:
            return {'message': f'No colin ids found'}, HTTPStatus.NOT_FOUND

        return {'maxId': last_event_id[0]}, HTTPStatus.OK if request.method == 'GET' else HTTPStatus.CREATED

    @staticmethod
    @cors.crossdomain(origin='*')
    @jwt.requires_auth
    def post(colin_id):
        """Add a row to the colin_last_update table."""
        try:
            # check authorization
            if not jwt.validate_roles([COLIN_SVC_ROLE]):
                return jsonify({'message': 'You are not authorized to update this table'}), HTTPStatus.UNAUTHORIZED
            db.session.execute(
                f"""
                insert into colin_last_update (last_update, last_event_id)
                values (current_timestamp, {colin_id})
                """
            )
            db.session.commit()
            return ColinLastUpdate.get()

        except Exception as err:  # pylint: disable=broad-except
            current_app.logger.error(f'Error updating colin_last_update table in legal db: {err}')
            return {f'message: failed to update colin_last_update.', 500}
