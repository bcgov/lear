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
import copy
from datetime import datetime as _datetime
from http import HTTPStatus
from typing import Generic, Optional, Tuple, TypeVar, Union

import requests  # noqa: I001; grouping out of order to make both pylint & isort happy
from requests import exceptions  # noqa: I001; grouping out of order to make both pylint & isort happy
from flask import current_app, g, jsonify, request
from flask_babel import _
from flask_cors import cross_origin
from flask_jwt_oidc import JwtManager
from flask_pydantic import validate as pydantic_validate
from html_sanitizer import Sanitizer  # noqa: I001;
from pydantic import BaseModel  # noqa: I001; pylint: disable=E0611; not sure why pylint is unable to scan module
from pydantic.generics import GenericModel
from werkzeug.local import LocalProxy

import legal_api.reports
from legal_api.constants import BOB_DATE
from legal_api.core import Filing as CoreFiling
from legal_api.exceptions import BusinessException
from legal_api.models import Address, Business, Filing, OfficeType, RegistrationBootstrap, User, UserRoles, db
from legal_api.models.colin_event_id import ColinEventId
from legal_api.schemas import rsbc_schemas
from legal_api.services import (
    STAFF_ROLE,
    SYSTEM_ROLE,
    DocumentMetaService,
    MinioService,
    RegistrationBootstrapService,
    authorized,
    namex,
    queue,
)
from legal_api.services.authz import is_allowed
from legal_api.services.filings import validate
from legal_api.services.utils import get_str
from legal_api.utils import datetime
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime
from legal_api.utils.util import build_schema_error_response

from ..bp import bp
# noqa: I003; the multiple route decorators cause an erroneous error in line space counting


class QueryModel(BaseModel):
    """Query string model."""

    draft: Optional[bool]
    only_validate: Optional[bool]


FilingT = TypeVar('FilingT')


class FilingModel(GenericModel, Generic[FilingT]):
    """Generic model to alow pydantic validation."""

    data: Optional[FilingT]


@bp.route('/<string:identifier>/filings', methods=['GET'])
@bp.route('/<string:identifier>/filings/<int:filing_id>', methods=['GET'])
@cross_origin(origin='*')
@jwt.requires_auth
@pydantic_validate(query=QueryModel)
def get_filings(identifier: str, filing_id: Optional[int] = None):
    """Return a JSON object with meta information about the Filing Submission."""
    if filing_id or identifier.startswith('T'):
        return ListFilingResource.get_single_filing(identifier, filing_id)

    return ListFilingResource.get_ledger_listing(identifier, jwt)


@bp.route('/<string:identifier>/filings', methods=['POST'])
@bp.route('/<string:identifier>/filings/<int:filing_id>', methods=['POST', 'PUT'])
@cross_origin(origin='*')
@jwt.requires_auth
@pydantic_validate()
def saving_filings(body: FilingModel,  # pylint: disable=too-many-return-statements,too-many-locals
                   query: QueryModel,
                   identifier,
                   filing_id: Optional[int] = None):
    """Modify an incomplete filing for the business."""
    # basic checks
    business = Business.find_by_identifier(identifier)
    err_msg, err_code = ListFilingResource.put_basic_checks(identifier, filing_id, request, business)
    if err_msg:
        return jsonify({'errors': [err_msg, ]}), err_code
    json_input = request.get_json()

    # check authorization
    response, response_code = ListFilingResource.check_authorization(identifier, json_input, business, filing_id)
    if response:
        return response, response_code

    # get header params
    payment_account_id = request.headers.get('account-id', request.headers.get('accountId', None))

    if not query.draft \
            and not ListFilingResource.is_historical_colin_filing(json_input) \
            and not ListFilingResource.is_before_epoch_filing(json_input, business):
        if identifier.startswith('T'):
            business_validate = RegistrationBootstrap.find_by_identifier(identifier)
        else:
            business_validate = business
        err = validate(business_validate, json_input, payment_account_id)
        if err or query.only_validate:
            if err:
                json_input['errors'] = err.msg
                return jsonify(json_input), err.code
            return jsonify(json_input), HTTPStatus.OK

    # save filing, if it's draft only then bail
    user = User.get_or_create_user_by_jwt(g.jwt_oidc_token_info)
    try:
        business, filing, err_msg, err_code = ListFilingResource.save_filing(request, identifier, user, filing_id)
        if err_msg or query.draft:
            reply = filing.json if filing else json_input
            reply['errors'] = [err_msg, ]
            return jsonify(reply), err_code or \
                (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)
    except Exception as err:
        print(err)

    # complete filing
    response, response_code = ListFilingResource.complete_filing(business, filing, query.draft, payment_account_id)
    if response and (response_code != HTTPStatus.CREATED or filing.source == Filing.Source.COLIN.value):
        return response, response_code

    # all done
    filing_json = filing.json
    if response:
        filing_json['filing']['header'].update(response)
    return jsonify(filing_json), \
        (HTTPStatus.CREATED if (request.method == 'POST') else HTTPStatus.ACCEPTED)


@bp.route('/<string:identifier>/filings', methods=['DELETE'])
@bp.route('/<string:identifier>/filings/<int:filing_id>', methods=['DELETE'])
@cross_origin(origin='*')
@jwt.requires_auth
def delete_filings(identifier, filing_id=None):
    """Delete a filing from the business."""
    if not filing_id:
        return ({'message':
                 _('No filing id provided for:') + identifier},
                HTTPStatus.BAD_REQUEST)

    # check authorization
    if not authorized(identifier, jwt, action=['edit']):
        return jsonify({'message':
                        _('You are not authorized to delete a filing for:') + identifier}), \
            HTTPStatus.UNAUTHORIZED

    if identifier.startswith('T'):
        filing = Filing.get_temp_reg_filing(identifier, filing_id)
    else:
        filing = Business.get_filing_by_id(identifier, filing_id)

    if not filing:
        return jsonify({'message': _('Filing Not Found.')}), HTTPStatus.NOT_FOUND

    if filing.deletion_locked:  # should not be deleted
        return ListFilingResource.create_deletion_locked_response(identifier, filing)

    try:
        ListFilingResource.delete_from_minio(filing)
        filing.delete()
    except BusinessException as err:
        return jsonify({'errors': [{'error': err.error}, ]}), err.status_code

    if identifier.startswith('T'):
        bootstrap = RegistrationBootstrap.find_by_identifier(identifier)
        if bootstrap:
            deregister_status = RegistrationBootstrapService.deregister_bootstrap(bootstrap)
            delete_status = RegistrationBootstrapService.delete_bootstrap(bootstrap)
            if deregister_status != HTTPStatus.OK or delete_status != HTTPStatus.OK:
                current_app.logger.error('Unable to deregister and delete temp reg:', identifier)

    return jsonify({'message': _('Filing deleted.')}), HTTPStatus.OK


@bp.route('/<string:identifier>/filings/<int:filing_id>', methods=['PATCH'])
@cross_origin(origin='*')
@jwt.requires_auth
def patch_filings(identifier, filing_id=None):
    """Cancel the payment and resets the filing status to DRAFT."""
    if not filing_id:
        return ({'message':
                 _('No filing id provided for:') + identifier},
                HTTPStatus.BAD_REQUEST)

    # check authorization
    if not authorized(identifier, jwt, action=['edit']):
        return jsonify({'message':
                        _('You are not authorized to delete a filing for:') + identifier}), \
            HTTPStatus.UNAUTHORIZED

    if identifier.startswith('T'):
        q = db.session.query(Filing). \
            filter(Filing.temp_reg == identifier).\
            filter(Filing.id == filing_id)

        filing = q.one_or_none()
    else:
        filing = Business.get_filing_by_id(identifier, filing_id)

    if not filing:
        return jsonify({'message': ('Filing Not Found.')}), \
            HTTPStatus.NOT_FOUND

    try:
        payment_svc_url = '{}/{}'.format(current_app.config.get('PAYMENT_SVC_URL'), filing.payment_token)
        token = jwt.get_token_auth_header()
        headers = {'Authorization': 'Bearer ' + token}
        rv = requests.delete(url=payment_svc_url, headers=headers, timeout=20.0)
        if rv.status_code in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
            filing.reset_filing_to_draft()

    except (exceptions.ConnectionError, exceptions.Timeout) as err:
        current_app.logger.error(f'Payment connection failure for {identifier}: filing:{filing.id}', err)
        return {'errors':
                [{'message': 'Unable to cancel payment for the filing.'}]
                }, HTTPStatus.INTERNAL_SERVER_ERROR

    except BusinessException as err:
        return {'errors': [{'message': err.error}]}, err.status_code

    return jsonify(filing.json), HTTPStatus.ACCEPTED


class ListFilingResource():
    """Business Filings service."""

    @staticmethod
    def get_single_filing(identifier: str, filing_id: int):
        """Return a single filing and all of its components."""
        original_filing = str(request.args.get('original', None)).lower() == 'true'
        rv = CoreFiling.get(identifier, filing_id)
        if not rv:
            return jsonify({'message': f'{identifier} no filings found'}), HTTPStatus.NOT_FOUND

        if original_filing:
            return jsonify(rv.redacted(rv.raw, jwt))

        if str(request.accept_mimetypes) == 'application/pdf':
            report_type = request.args.get('type', None)
            return legal_api.reports.get_pdf(rv.storage, report_type)

        filing_json = rv.json
        if documents := DocumentMetaService().get_documents(filing_json):
            filing_json['filing']['documents'] = documents

        if filing_json.get('filing', {}).get('header', {}).get('status') == Filing.Status.PENDING.value:
            ListFilingResource.get_payment_update(filing_json)

        filing_json = {**filing_json, **CoreFiling.common_ledger_items(identifier, rv.storage)}

        return jsonify(rv.redacted(filing_json, jwt))

    @staticmethod
    def get_payment_update(filing_dict: dict):
        """Get update on the payment status from the pay service."""
        try:
            headers = {
                'Authorization': f'Bearer {jwt.get_token_auth_header()}',
                'Content-Type': 'application/json'
            }
            payment_svc_url = current_app.config.get('PAYMENT_SVC_URL')

            if payment_token := filing_dict.get('filing', {}).get('header', {}).get('paymentToken'):
                pay_response = requests.get(
                    url=f'{payment_svc_url}/{payment_token}',
                    headers=headers
                )
                pay_details = {
                    'isPaymentActionRequired': pay_response.json().get('isPaymentActionRequired', False),
                    'paymentMethod': pay_response.json().get('paymentMethod', '')
                }
                filing_dict['filing']['header'].update(pay_details)

        except (exceptions.ConnectionError, exceptions.Timeout) as err:
            current_app.logger.error(
                f'Payment connection failure for getting payment_token:{payment_token} filing payment details. ', err)

    @staticmethod
    def get_ledger_listing(identifier: str, user_jwt: JwtManager):
        """Return the requested ledger for the business identifier provided."""
        # Does it make sense to get a PDF of all filings?
        if str(request.accept_mimetypes) == 'application/pdf':
            return jsonify({'message': _('Cannot return a single PDF of multiple filing submissions.')}), \
                HTTPStatus.NOT_ACCEPTABLE

        ledger_start = request.args.get('start', default=None, type=int)
        ledger_size = request.args.get('size', default=None, type=int)
        datetime_str = request.args.get('effective_date', default=None)

        effective_date = None
        if datetime_str:
            if not ListFilingResource._is_valid_date(datetime_str):
                return ({'message': 'Invalid Date format.'}, HTTPStatus.BAD_REQUEST)
            else:
                effective_date = _datetime.fromisoformat(datetime_str)

        business = Business.find_by_identifier(identifier)

        if not business:
            return jsonify(filings=[]), HTTPStatus.NOT_FOUND

        filings = CoreFiling.ledger(business.id,
                                    jwt=user_jwt,
                                    statuses=[Filing.Status.COMPLETED.value, Filing.Status.PAID.value],
                                    start=ledger_start,
                                    size=ledger_size,
                                    effective_date=effective_date)

        return jsonify(filings=filings)

    @staticmethod
    def _is_valid_date(datetime_str):
        try:
            _datetime.fromisoformat(datetime_str)
        except ValueError:
            return False
        return True

    @staticmethod
    def create_deletion_locked_response(identifier, filing):
        """Create a filing that draft that cannot be deleted."""
        business = Business.find_by_identifier(identifier)
        if (filing.status == Filing.Status.DRAFT.value and
                filing.filing_type == 'alteration' and
                business.legal_type in [lt.value for lt in (Business.LIMITED_COMPANIES +
                                                            Business.UNLIMITED_COMPANIES)]):
            response = jsonify({
                'message': _('You must complete this alteration filing to become a BC Benefit Company.')
            }), HTTPStatus.UNAUTHORIZED
        else:
            response = jsonify({
                'message': _('This filing cannot be deleted at this moment.')
            }), HTTPStatus.UNAUTHORIZED

        return response

    @staticmethod
    def check_and_update_nr(filing):
        """Check and update NR to extend expiration date as needed."""
        # if this is an incorporation filing for a name request
        if filing.filing_type in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            nr_number = filing.json['filing'][filing.filing_type]['nameRequest'].get('nrNumber', None)
            effective_date = filing.json['filing']['header'].get('effectiveDate', None)
            if effective_date:
                effective_date = datetime.datetime.fromisoformat(effective_date)
            if nr_number:
                nr_response = namex.query_nr_number(nr_number)
                # If there is an effective date, check if we need to extend the NR expiration
                if effective_date and namex.is_date_past_expiration(nr_response.json(), effective_date):
                    namex.update_nr_as_future_effective(nr_response.json(), effective_date)

    @staticmethod
    def complete_filing(business, filing, draft, payment_account_id) -> Tuple[dict, int]:
        """Complete the filing, either to COLIN or by getting an invoice.

        Used for encapsulation of common functionality used in Filing and Business endpoints.
        """
        # if filing is from COLIN, place on queue and return
        if filing.source == Filing.Source.COLIN.value:
            err_msg, err_code = ListFilingResource.process_colin_filing(business.identifier, filing, business)
            return jsonify(err_msg), err_code

        # create invoice
        if not draft:
            # Check if this is an nr and update as needed
            ListFilingResource.check_and_update_nr(filing)

            filing_types = ListFilingResource.get_filing_types(business, filing.filing_json)
            pay_msg, pay_code = ListFilingResource.create_invoice(business,
                                                                  filing,
                                                                  filing_types,
                                                                  jwt,
                                                                  payment_account_id)
            if pay_msg and pay_code != HTTPStatus.CREATED:
                reply = filing.json
                reply['errors'] = [pay_msg, ]
                return jsonify(reply), pay_code
            ListFilingResource.set_effective_date(business, filing)
            return pay_msg, pay_code

        return None, None

    @staticmethod
    def put_basic_checks(identifier, filing_id, client_request, business) -> Tuple[dict, int]:
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

        filing_type = json_input.get('filing', {}).get('header', {}).get('name')
        if not filing_type:
            return ({'message': 'filing/header/name is a required property'}, HTTPStatus.BAD_REQUEST)

        if filing_type not in CoreFiling.NEW_BUSINESS_FILING_TYPES and business is None:
            return ({'message': 'A valid business is required.'}, HTTPStatus.BAD_REQUEST)

        return None, None

    @staticmethod
    def check_authorization(identifier, filing_json: dict,
                            business: Business,
                            filing_id: int = None) -> Tuple[dict, int]:
        """Assert that the user can access the business."""
        filing_type = filing_json['filing']['header'].get('name')
        filing_sub_type = Filing.get_filings_sub_type(filing_type, filing_json)

        # While filing IA business object will be None. Setting default values in that case.
        state = business.state if business else Business.State.ACTIVE
        # for incorporationApplication and registration, get legalType from nameRequest
        legal_type = business.legal_type if business else \
            filing_json['filing'][filing_type]['nameRequest'].get('legalType')

        if not authorized(identifier, jwt, action=['edit']) or \
                not is_allowed(business, state, filing_type, legal_type, jwt, filing_sub_type, filing_id):
            return jsonify({'message':
                            f'You are not authorized to submit a filing for {identifier}.'}), \
                HTTPStatus.UNAUTHORIZED

        return None, None

    @staticmethod
    def is_before_epoch_filing(filing_json: str, business: Business):
        """Is the filings before the launch of COOPS."""
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
    def is_historical_colin_filing(filing_json: str):
        """Is the filing a filing marked historical in COLIN."""
        if (filing_header := filing_json.get('filing', {}).get('header')) \
            and filing_header.get('source', None) == 'COLIN' \
                and filing_header.get('date') < BOB_DATE:
            return True

        return False

    @staticmethod
    def process_colin_filing(identifier: str, filing: Filing, business: Business) -> Tuple[dict, int]:
        """Manage COLIN sourced filings."""
        try:
            if not filing.colin_event_ids:
                raise KeyError

            if (epoch_filing :=
                    Filing.get_filings_by_status(business_id=business.id, status=[Filing.Status.EPOCH.value])
                ) and \
                    ListFilingResource.is_before_epoch_filing(filing.filing_json, business):
                filing.transaction_id = epoch_filing[0].transaction_id
                filing.set_processed(business.legal_type)
                filing.save()
            else:
                payload = {'filing': {'id': filing.id}}
                queue.publish_json(payload)

            return {'filing': {'id': filing.id}}, HTTPStatus.CREATED
        except KeyError:
            current_app.logger.error('Business:%s missing filing/header/colinIds, unable to post to queue',
                                     identifier)
            return {'errors': {'message': 'missing filing/header/colinIds'}}, HTTPStatus.BAD_REQUEST
        except Exception as err:  # pylint: disable=broad-except; final catch
            current_app.logger.error('Business:%s unable to post to queue, err=%s', identifier, err)
            return {'errors': {'message': 'unable to publish for post processing'}}, HTTPStatus.BAD_REQUEST

    @staticmethod
    def save_filing(client_request: LocalProxy,  # pylint: disable=too-many-return-statements,too-many-branches
                    business_identifier: str,
                    user: User,
                    filing_id: int) -> Tuple[Union[Business, RegistrationBootstrap], Filing, dict, int]:
        """Save the filing to the ledger.

        If not successful, a dict of errors is returned.

        Returns: {
            Business: business model object found for the identifier provided
            Filing: filing model object for the submitted filing
            dict: a dict of errors
            int: the HTTPStatus error code

        @TODO refactor to a set of single putpose routines
        }
        """
        json_input = client_request.get_json()
        if not json_input:
            return None, None, {'message':
                                f'No filing json data in body of post for {business_identifier}.'}, \
                HTTPStatus.BAD_REQUEST

        if business_identifier.startswith('T'):
            # bootstrap filing
            bootstrap = RegistrationBootstrap.find_by_identifier(business_identifier)
            business = None
            if not bootstrap:
                return None, None, {'message':
                                    f'{business_identifier} not found'}, HTTPStatus.NOT_FOUND
            if client_request.method == 'PUT':
                rv = db.session.query(Filing). \
                    filter(Filing.temp_reg == business_identifier). \
                    filter(Filing.id == filing_id). \
                    one_or_none()
                if not rv:
                    return None, None, {'message':
                                        f'{business_identifier} no filings found'}, HTTPStatus.NOT_FOUND
                filing = rv
            else:
                filing = Filing()
                filing.temp_reg = bootstrap.identifier
                if not json_input['filing'].get('business'):
                    json_input['filing']['business'] = {}
                json_input['filing']['business']['identifier'] = bootstrap.identifier

        else:
            # regular filing for a business
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
            filing.source = filing.filing_json['filing']['header'].get('source', Filing.Source.LEAR.value)
            if filing.source == Filing.Source.COLIN.value:
                try:
                    filing.filing_date = datetime.datetime.fromisoformat(filing.filing_json['filing']['header']['date'])
                    for colin_id in filing.filing_json['filing']['header']['colinIds']:
                        colin_event_id = ColinEventId()
                        colin_event_id.colin_event_id = colin_id
                        filing.colin_event_ids.append(colin_event_id)
                except KeyError:
                    current_app.logger.error('Business:%s missing filing/header values, unable to save',
                                             business.identifier)
                    return None, None, {'message': 'missing filing/header values'}, HTTPStatus.BAD_REQUEST
            else:
                filing.filing_date = datetime.datetime.utcnow()

            # for any legal type, set effective date as set in json; otherwise leave as default
            filing.effective_date = \
                datetime.datetime.fromisoformat(filing.filing_json['filing']['header']['effectiveDate']) \
                if filing.filing_json['filing']['header'].get('effectiveDate', None) else datetime.datetime.utcnow()

            filing.filing_json = ListFilingResource.sanitize_html_fields(filing.filing_json)
            filing.save()
        except BusinessException as err:
            return None, None, {'error': err.error}, err.status_code

        return business or bootstrap, filing, None, None

    @staticmethod
    def sanitize_html_fields(filing_json):
        """Sanitize HTML fields to prevent XSS."""
        # Need to sanitize as this can be HTML, which provides an easy way to inject JS scripts etc.
        # We have are using v-sanitize on the frontend, for fields that the user controls.
        # https://www.stackhawk.com/blog/vue-xss-guide-examples-and-prevention/
        if resolution_content := filing_json['filing'].get('specialResolution', {}).get('resolution', None):
            filing_json['filing']['specialResolution']['resolution'] = Sanitizer().sanitize(resolution_content)
        if resolution_content := filing_json['filing'].get('correction', {}).get('resolution', None):
            filing_json['filing']['correction']['resolution'] = Sanitizer().sanitize(resolution_content)
        return filing_json

    @staticmethod
    def validate_filing_json(client_request: LocalProxy) -> Tuple[dict, int]:
        """Assert that the json is a valid filing.

        Returns: {
            dict: a dict, success message or array of errors
            int: the HTTPStatus error code
        }
        """
        valid, err = rsbc_schemas.validate(client_request.get_json(), 'filing')

        if valid:
            return {'message': 'Filing is valid'}, HTTPStatus.OK

        errors = build_schema_error_response(err)
        return errors, HTTPStatus.BAD_REQUEST

    @staticmethod
    def get_filing_types(business: Business, filing_json: dict):  # pylint: disable=too-many-branches
        """Get the filing type fee codes for the filing.

        Returns: {
            list: a list, filing type fee codes in the filing
        }
        """
        filing_types = []
        priority_flag = filing_json['filing']['header'].get('priority', False)
        filing_type = filing_json['filing']['header'].get('name', None)
        waive_fees_flag = filing_json['filing']['header'].get('waiveFees', False)

        if filing_type in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            legal_type = filing_json['filing'][filing_type]['nameRequest']['legalType']
        else:
            legal_type = business.legal_type

        if any('correction' in x for x in filing_json['filing'].keys()):
            filing_type_code = Filing.FILINGS.get('correction', {}).get('codes', {}).get(legal_type)
            filing_types.append({
                'filingTypeCode': filing_type_code,
                'priority': priority_flag,
                'waiveFees': waive_fees_flag
            })
        elif filing_type == 'dissolution':
            dissolution_type = filing_json['filing']['dissolution']['dissolutionType']
            if dissolution_type == 'voluntary':
                filing_type_code = Filing.FILINGS.get('dissolution', {}).get(dissolution_type).get('codes', {}) \
                    .get(legal_type)
                filing_types.append({
                    'filingTypeCode': filing_type_code,
                    'futureEffective': ListFilingResource.is_future_effective_filing(filing_json),
                    'priority': priority_flag,
                    'waiveFees': waive_fees_flag
                })
                if legal_type == Business.LegalTypes.COOP.value:
                    filing_type_code =\
                        Filing.FILINGS.get('specialResolution', {}).get('codes', {}).get(Business.LegalTypes.COOP.value)
                    filing_types.append({
                        'filingTypeCode': filing_type_code,
                        'priority': priority_flag,
                        'waiveFees': waive_fees_flag
                    })
                    filing_type_code =\
                        Filing.FILINGS.get('affidavit', {}).get('codes', {}).get(Business.LegalTypes.COOP.value)
                    filing_types.append({
                        'filingTypeCode': filing_type_code,
                        'waiveFees': waive_fees_flag
                    })
            elif dissolution_type == 'administrative':
                filing_types.append({
                    'filingTypeCode': 'NOFEE',
                    'waiveFees': waive_fees_flag
                })
        elif filing_type in ['courtOrder', 'registrarsNotation', 'registrarsOrder', 'putBackOn', 'adminFreeze']:
            filing_type_code = Filing.FILINGS.get(filing_type, {}).get('code')
            filing_types.append({
                'filingTypeCode': filing_type_code,
                'filingDescription': filing_type
            })
        else:
            for k in filing_json['filing'].keys():
                filing_sub_type = Filing.get_filings_sub_type(k, filing_json)
                priority = priority_flag
                if filing_sub_type:
                    filing_type_code = \
                        Filing.FILINGS.get(k, {}).get(filing_sub_type, {}).get('codes', {}).get(legal_type)
                else:
                    filing_type_code = Filing.FILINGS.get(k, {}).get('codes', {}).get(legal_type)

                # check if changeOfDirectors is a free filing
                if k == 'changeOfDirectors':
                    free = True
                    free_changes = ['nameChanged', 'addressChanged']
                    for director in filing_json['filing'][k].get('directors'):
                        # if changes other than name/address change then this is not a free filing
                        if not all(change in free_changes for change in director.get('actions', [])):
                            free = False
                            break
                    filing_type_code = Filing.FILINGS[k].get('free', {}).get('codes', {}).get(legal_type)\
                        if free else Filing.FILINGS[k].get('codes', {}).get(legal_type)

                # check if priority handled in parent filing
                if k in ['changeOfDirectors', 'changeOfAddress']:
                    priority = False if filing_type == 'annualReport' else priority_flag

                if k in ['incorporationApplication', 'amalgamationApplication', 'continuationIn', 'alteration']:
                    filing_types.append({
                        'filingTypeCode': filing_type_code,
                        'futureEffective': ListFilingResource.is_future_effective_filing(filing_json),
                        'priority': priority,
                        'waiveFees': waive_fees_flag
                    })
                elif filing_type_code:
                    filing_types.append({
                        'filingTypeCode': filing_type_code,
                        'priority': priority,
                        'waiveFees': waive_fees_flag
                    })
        return filing_types

    @staticmethod
    def create_invoice(business: Business,  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
                       filing: Filing,
                       filing_types: list,
                       user_jwt: JwtManager,
                       payment_account_id: str = None) \
            -> Tuple[int, dict, int]:
        """Create the invoice for the filing submission.

        Returns: {
            int: the paymentToken (id), or None
            dict: a dict of errors, or None
            int: the HTTPStatus error code, or None
        }
        """
        payment_svc_url = current_app.config.get('PAYMENT_SVC_URL')

        if filing.filing_type in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            office_type = OfficeType.REGISTERED
            if filing.filing_type == Filing.FILINGS['registration']['name']:
                office_type = OfficeType.BUSINESS

            mailing_address = Address.create_address(
                filing.json['filing'][filing.filing_type]['offices'][office_type]['mailingAddress'])
            corp_type = filing.json['filing'][filing.filing_type]['nameRequest'].get(
                'legalType', Business.LegalTypes.BCOMP.value)

            try:
                business.legal_name = filing.json['filing'][filing.filing_type]['nameRequest']['legalName']
            except KeyError:
                business.legal_name = business.identifier
        elif filing.filing_type == Filing.FILINGS['conversion']['name']:
            if (mailing_address_json :=
                filing.json['filing']['conversion']
                    .get('offices', {})
                    .get('businessOffice', {}).get('mailingAddress', None)):
                mailing_address = Address.create_address(mailing_address_json)
            else:
                mailing_address = business.mailing_address.one_or_none()
            corp_type = business.legal_type if business.legal_type else \
                filing.json['filing']['business'].get('legalType')
        else:
            mailing_address = business.mailing_address.one_or_none()
            corp_type = business.legal_type if business.legal_type else \
                filing.json['filing']['business'].get('legalType')

        payload = {
            'businessInfo': {
                'businessIdentifier': f'{business.identifier}',
                'corpType': f'{corp_type}',
                'businessName': f'{business.legal_name}',
                'contactInfo': {'city': mailing_address.city,
                                'postalCode': mailing_address.postal_code,
                                'province': mailing_address.region,
                                'addressLine1': mailing_address.street,
                                'country': mailing_address.country}
            },
            'filingInfo': {
                'filingIdentifier': f'{filing.id}',
                'filingTypes': filing_types
            },
            'details': ListFilingResource.details_for_invoice(business.identifier, corp_type)
        }
        folio_number = filing.json['filing']['header'].get('folioNumber', None)
        if folio_number:
            payload['filingInfo']['folioNumber'] = folio_number

        if user_jwt.validate_roles([STAFF_ROLE]):
            special_role = UserRoles.staff
        elif user_jwt.validate_roles([SYSTEM_ROLE]):
            special_role = UserRoles.system
        else:
            special_role = None

        if special_role:
            account_info = {}
            routing_slip_number = get_str(filing.filing_json, 'filing/header/routingSlipNumber')
            if routing_slip_number:
                account_info['routingSlip'] = routing_slip_number
            bcol_account_number = get_str(filing.filing_json, 'filing/header/bcolAccountNumber')
            if bcol_account_number:
                account_info['bcolAccountNumber'] = bcol_account_number
            dat_number = get_str(filing.filing_json, 'filing/header/datNumber')
            if dat_number:
                account_info['datNumber'] = dat_number

            if account_info:
                payload['accountInfo'] = account_info
        try:
            token = user_jwt.get_token_auth_header()
            headers = {'Authorization': 'Bearer ' + token,
                       'Content-Type': 'application/json'}
            rv = requests.post(url=payment_svc_url,
                               json=payload,
                               headers=headers,
                               timeout=20.0)
        except (exceptions.ConnectionError, exceptions.Timeout) as err:
            current_app.logger.error(f'Payment connection failure for {business.identifier}: filing:{filing.id}', err)
            return {'message': 'unable to create invoice for payment.'}, HTTPStatus.PAYMENT_REQUIRED

        if rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            pid = rv.json().get('id')
            filing.payment_token = pid
            filing.payment_status_code = rv.json().get('statusCode', '')
            filing.payment_account = payment_account_id
            filing.submitter_roles = special_role

            filing.save()
            return {'isPaymentActionRequired': rv.json().get('isPaymentActionRequired', False)}, HTTPStatus.CREATED

        if rv.status_code == HTTPStatus.BAD_REQUEST:
            # Set payment error type used to retrieve error messages from pay-api
            error_type = rv.json().get('type')
            filing.payment_status_code = error_type
            filing.save()

            return {'payment_error_type': error_type,
                    'message': rv.json().get('detail')}, HTTPStatus.PAYMENT_REQUIRED

        return {'message': 'unable to create invoice for payment.'}, HTTPStatus.PAYMENT_REQUIRED

    @staticmethod
    def set_effective_date(business: Business, filing: Filing):
        """Set the effective date of the Filing."""
        filing_type = filing.filing_json['filing']['header']['name']
        if filing_type in CoreFiling.NEW_BUSINESS_FILING_TYPES:
            if fe_date := filing.filing_json['filing']['header'].get('futureEffectiveDate'):
                filing.effective_date = datetime.datetime.fromisoformat(fe_date)
                filing.save()

        elif business.legal_type != Business.LegalTypes.COOP.value and filing_type == 'changeOfAddress':
            effective_date = LegislationDatetime.tomorrow_midnight()
            effective_date_utc = LegislationDatetime.as_utc_timezone(effective_date)
            filing_json_update = copy.deepcopy(filing.filing_json)
            filing_json_update['filing']['header']['futureEffectiveDate'] = effective_date_utc.isoformat()
            filing._filing_json = filing_json_update  # pylint: disable=protected-access;
            filing.effective_date = effective_date
            filing.save()

    @staticmethod
    def is_future_effective_filing(filing_json: dict) -> bool:
        """Return True if the filing is a FED."""
        is_future_effective = False
        effective_date = datetime.datetime.fromisoformat(filing_json['filing']['header']['effectiveDate']) \
            if filing_json['filing']['header'].get('effectiveDate', None) else None
        if effective_date:
            is_future_effective = effective_date > datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        return is_future_effective

    @staticmethod
    def delete_from_minio(filing):
        """Delete file from minio."""
        if (filing.filing_type == Filing.FILINGS['incorporationApplication'].get('name')
                and (cooperative := filing.filing_json
                     .get('filing', {})
                     .get('incorporationApplication', {})
                     .get('cooperative', None))) or \
            (filing.filing_type == Filing.FILINGS['alteration'].get('name')
                and (cooperative := filing.filing_json
                     .get('filing', {})
                     .get('alteration', {}))):
            if rules_file_key := cooperative.get('rulesFileKey', None):
                MinioService.delete_file(rules_file_key)
            if memorandum_file_key := cooperative.get('memorandumFileKey', None):
                MinioService.delete_file(memorandum_file_key)
        elif filing.filing_type == Filing.FILINGS['dissolution'].get('name') \
                and (affidavit_file_key := filing.filing_json
                     .get('filing', {})
                     .get('dissolution', {})
                     .get('affidavitFileKey', None)):
            MinioService.delete_file(affidavit_file_key)
        elif filing.filing_type == Filing.FILINGS['courtOrder'].get('name') \
                and (file_key := filing.filing_json
                     .get('filing', {})
                     .get('courtOrder', {})
                     .get('fileKey', None)):
            MinioService.delete_file(file_key)
        elif filing.filing_type == Filing.FILINGS['continuationIn'].get('name'):
            continuation_in = filing.filing_json.get('filing', {}).get('continuationIn', {})

            # Delete affidavit file
            if affidavit_file_key := continuation_in.get('foreignJurisdiction', {}).get('affidavitFileKey', None):
                MinioService.delete_file(affidavit_file_key)

            # Delete authorization file(s)
            authorization_files = continuation_in.get('authorization', {}).get('files', [])
            for file in authorization_files:
                if auth_file_key := file.get('fileKey', None):
                    MinioService.delete_file(auth_file_key)

    @staticmethod
    def details_for_invoice(business_identifier: str, corp_type: str):
        """Generate details for invoice."""
        # Avoid temporary identifiers.
        if not business_identifier or business_identifier.startswith('T'):
            return []
        return [
            {
                'label': 'Registration Number:' if corp_type in ('SP', 'GP') else 'Incorporation Number:',
                'value': f'{business_identifier}'
            }
        ]
