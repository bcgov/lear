# Copyright © 2021 Province of British Columbia
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
"""Retrieve the summary for the entity."""
from http import HTTPStatus

from flask import jsonify, request
from flask_cors import cross_origin

from legal_api.exceptions import ErrorCode, get_error_message
from legal_api.models import Business
from legal_api.reports import get_business_summary
from legal_api.services import authorized
from legal_api.utils.auth import jwt

from .bp import bp


@bp.route('/<string:identifier>/summary', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*')
@jwt.requires_auth
def get_summary(identifier):
    """Return the business summary."""
    # basic checks
    if not authorized(identifier, jwt, ['view', ]):
        return jsonify(
            message=get_error_message(ErrorCode.NOT_AUTHORIZED, **{'identifier': identifier})
        ), HTTPStatus.UNAUTHORIZED

    business = Business.find_by_identifier(identifier)

    if not business:
        return jsonify(
            message=get_error_message(ErrorCode.MISSING_BUSINESS, **{'identifier': identifier})
        ), HTTPStatus.NOT_FOUND

    if 'application/pdf' in request.accept_mimetypes:
        return get_business_summary(business)
    return {}, HTTPStatus.NOT_FOUND
